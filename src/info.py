from collections import defaultdict

import csv
import json
from typing import List, Dict, Tuple, Set

from src.factor import Value, ValueType, AbstractFactor
from src.keywords import DataType
from src.rest import RestOp


class RuntimeInfoManager:
    def __init__(self, config):
        self._config = config
        self._num_of_requests = 0
        self.llm_call = 0
        self.call_time = 0
        self.prompt_tokens = 0
        self.cost = 0
        self._response_chains: List[Dict[RestOp, object]] = [dict()]
        self._response_dict: Dict[RestOp, List[object]] = dict()
        self._unresolved_params: Set[Tuple[RestOp, str]] = set()

        self._param_to_ask: Dict[RestOp, Set[AbstractFactor]] = dict()
        self._constraint_params: Dict[RestOp, Set[AbstractFactor]] = dict()
        self._idl: Dict[RestOp, List[str]] = dict()
        self._pict: Dict[RestOp, List[str]] = dict()
        self._path_binding: Dict[RestOp, Dict[AbstractFactor, List[RestOp]]] = dict()
        self._param_binding: Dict[RestOp, Dict[AbstractFactor, Dict[RestOp, str]]] = dict()

        self._reused_essential_seq_dict: Dict[Tuple[RestOp], List[Dict[str, Value]]] = defaultdict(list)
        self._reused_all_p_seq_dict: dict = defaultdict(list)
        self._ok_value_dict: Dict[str, List[Value]] = defaultdict(list)
        self._success_sequence: set = set()
        self._success_operations: set = set()

        self._response_list = dict()
        self._example_value_dict: Dict[str, Dict[str, List[str, int]]] = dict()
        self._test_case_dict = dict()

    def get_chains(self, max_chain_items):
        sortedList = sorted(self._response_chains, key=lambda c: len(c.keys()), reverse=True)
        return sortedList[:max_chain_items] if max_chain_items < len(sortedList) else sortedList

    def get_reused_with_essential_p(self, operations: Tuple[RestOp]):
        reused_case = self._reused_essential_seq_dict.get(operations, list())
        if len(reused_case) > 0:
            return [{p: Value(v.val, ValueType.Reused, v.type) for p, v in case.items()} for case in reused_case]
        return []

    def get_reused_with_all_p(self, operations: Tuple[RestOp]):
        reused_case = self._reused_all_p_seq_dict.get(operations, list())
        if len(reused_case) > 0:
            return [{p: Value(v.val, ValueType.Reused, v.type) for p, v in case.items()} for case in reused_case]
        return []

    def is_unresolved(self, p_name):
        return p_name in self._unresolved_params

    def save_reuse(self, url_tuple, is_essential, case):
        if is_essential:
            to_dict = self._reused_essential_seq_dict
        else:
            to_dict = self._reused_all_p_seq_dict
        if len(to_dict[url_tuple]) < 10:
            to_dict[url_tuple].append(case)

    def save_ok_value(self, case):
        for paramStr, value in case.items():
            if paramStr not in self._ok_value_dict.keys():
                self._ok_value_dict[paramStr].append(value)
            else:
                lst = self._ok_value_dict.get(paramStr)
                if len(lst) < 10 and value not in lst:
                    lst.append(value)

    def save_chain(self, chain, operation, response):
        new_chain = chain.copy()
        new_chain[operation] = response
        self._response_chains.append(new_chain)
        if len(self._response_chains) > 10:
            self._response_chains.pop(0)

    def save_success_response(self, operation, response):
        if self._response_dict.get(operation) is None:
            self._response_dict[operation] = list()
        self._response_dict[operation].append(response)

    def get_success_responses(self, operation=None):
        if operation is None:
            return self._response_dict
        else:
            response = self._response_dict.get(operation, [])
            if len(response) == 0:
                return []
            else:
                return response

    @staticmethod
    def save_id_count(operation, response, id_counter):
        if isinstance(response, dict):
            iid = response.get("id")
            try:
                id_counter.append((iid, operation.path.__repr__()))
            except TypeError:
                pass
        elif isinstance(response, list):
            for r in response:
                iid = r.get("id")
                try:
                    id_counter.append((int(iid), operation.url))
                except TypeError:
                    pass
        else:
            pass

    def save_success_seq(self, url_tuple):
        self._success_sequence.add(url_tuple)

    def save_response(self, op, response_list, ca):
        value_set = set()
        for v_dict in ca:
            for p, v in v_dict.items():
                if v.type == DataType.String and v.val is not None and v.val != "":
                    value_set.add(v.val)
        if self._response_list.get(op.__repr__()) is None:
            self._response_list[op.__repr__()] = set()
        for sc, response in response_list:
            if sc >= 400:
                response = json.dumps(response)
                response = response.strip('"').replace('\\"', '"').replace('\\\\', '\\')
                for v in value_set:
                    if v in response and len(v) > 1:
                        response = response.replace(v, "*")
                        break
                self._response_list[op.__repr__()].add(response)

    def save_response_to_file(self):
        save_path = f"{self._config.data_path}/response.json"
        save_list = dict()
        for op, response_set in self._response_list.items():
            save_list[op] = list(response_set)
        with open(save_path, 'w') as f:
            json.dump(save_list, f, indent=2)

    def save_case_response(self, op, case, response_data, status_code):
        if self._test_case_dict.get(op.__repr__()) is None:
            self._test_case_dict[op.__repr__()] = list()
        self._test_case_dict[op.__repr__()].append((case, response_data, status_code))

    def save_case_response_to_file(self):
        save_path = f"{self._config.data_path}/case_response.json"
        with open(save_path, 'w') as f:
            json.dump(self._test_case_dict, f, indent=2)


    def save_problem_param(self, operation, param_list):
        if self._param_to_ask.get(operation) is None:
            self._param_to_ask[operation] = set()
        for f in operation.get_leaf_factors():
            if f.get_global_name in param_list:
                self._param_to_ask[operation].add(f)

    def get_problem_params(self, operation):
        return self._param_to_ask.get(operation, [])

    def get_constraint_params(self, operation):
        return self._constraint_params.get(operation, [])

    def save_constraint_params(self, operation, c_str_list):
        if self._constraint_params.get(operation) is None:
            self._constraint_params[operation] = set()
        for f in operation.get_leaf_factors():
            for c in c_str_list:
                if f.get_global_name in c:
                    self._constraint_params[operation].add(f)

    def save_idl(self, operation, idl_list):
        for idl_str in idl_list:
            if self._idl.get(operation) is None:
                self._idl[operation] = []
            self._idl[operation].append(idl_str)

    def get_idl(self, operation):
        return self._idl.get(operation, [])

    def save_pict(self, operation, idl_list):
        for idl_str in idl_list:
            if self._pict.get(operation) is None:
                self._pict[operation] = []
            self._pict[operation].append(idl_str)

    def get_pict(self, operation):
        return self._pict.get(operation, [])

    def clear_llm_result(self, operation):
        if self._param_to_ask.get(operation) is not None:
            self._param_to_ask[operation].clear()
        if self._constraint_params.get(operation) is not None:
            self._constraint_params[operation].clear()
        if self._idl.get(operation) is not None:
            self._idl[operation].clear()
        if self._pict.get(operation) is not None:
            self._pict[operation].clear()

    def save_constraint(self):
        idl_save_path = f"{self._config.data_path}/idl.csv"
        with open(idl_save_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for op, constraints in self._idl.items():
                if len(constraints) > 0:
                    for c in constraints:
                        writer.writerow([op.__repr__(), c])

        pict_save_path = f"{self._config.data_path}/pict.csv"
        with open(pict_save_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for op, constraints in self._pict.items():
                if len(constraints) > 0:
                    for c in constraints:
                        writer.writerow([op.__repr__(), c])

    def save_example_value(self, operation, response_list, ca):
        if self._example_value_dict.get(operation.__repr__()) is None:
            self._example_value_dict[operation.__repr__()] = dict()

        for index, (sc, response) in enumerate(response_list):
            if int(sc) < 400:
                case = ca[index]
                for p, v in case.items():
                    for f in operation.get_leaf_factors():
                        if f.get_global_name == p and v.val in f.llm_examples:
                            if self._example_value_dict[operation.__repr__()].get(p) is None:
                                self._example_value_dict[operation.__repr__()][p] = list()
                            if v.val not in self._example_value_dict[operation.__repr__()][p]:
                                self._example_value_dict[operation.__repr__()][p].append(v.val)

    def save_value_to_file(self):
        save_path = f"{self._config.data_path}/example_value.json"
        with open(save_path, 'w') as f:
            json.dump(self._example_value_dict, f, indent=2)

    def save_path_binding(self, operation, binding, param_list, operations):
        self._path_binding[operation] = dict()
        for f in param_list:
            op_str = binding.get(f.get_global_name)
            if op_str is not None:
                for op in operations:
                    if op.__repr__() == op_str:
                        self._path_binding[operation][f] = op
                        break

    def get_path_binding(self, operation):
        return self._path_binding.get(operation, dict())

    def bind_param(self, operation, response, param_list, operations):
        for f in param_list:
            if f.get_global_name in response:
                bind_info = response[f.get_global_name]
                dict_to_add = dict()
                for op in operations:
                    if op.__repr__() in bind_info:
                        param_str = bind_info[op.__repr__()]
                        dict_to_add[op] = param_str
                if self._param_binding.get(operation) is None:
                    self._param_binding[operation] = dict()
                self._param_binding[operation][f] = dict_to_add

    def get_param_binding(self, operation):
        return self._param_binding.get(operation, dict())
