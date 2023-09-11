import json
import time
import re
import requests
import subprocess
import shlex
import chardet
from dataclasses import dataclass
from src.Dto.keywords import Loc, DataType, Method
from pathlib import Path
from typing import List, Tuple, Dict, Union, Set
from src.Dto.operation import Operation
from src.Dto.constraint import Constraint, Processor
from src.Dto.parameter import AbstractParam, ValueType
from collections import defaultdict
from loguru import logger


def _saveChain(responseChains: List[dict], chain: dict, opStr: str, response):
    newChain = chain.copy()
    newChain[opStr] = response
    responseChains.append(newChain)
    if len(responseChains) > 10:
        responseChains.pop(0)


class ACTS:
    def __init__(self, dataPath, jar):
        self._workplace = Path(dataPath) / "acts"
        self.jar = jar
        if not self._workplace.exists():
            self._workplace.mkdir()

    @staticmethod
    def getId(paramName, paramNames):
        index = paramNames.index(paramName)
        return "P" + str(index)

    @staticmethod
    def getName(paramId: str, paramNames):
        index = int(paramId.lstrip("P"))
        return paramNames[index]

    def transformConstraint(self, domain_map, paramNames, constraint: Constraint):
        cStr = constraint.toActs(domain_map)
        if cStr is None:
            return ""
        for paramName in constraint.paramNames:
            pattern = r"\b" + paramName + r"\b"
            paramId = self.getId(paramName, paramNames)
            cStr = re.sub(re.compile(pattern), paramId, cStr)
        return eval(cStr)

    def writeInput(self, domain_map, paramNames, constraints, strength) -> Path:
        inputFile = self._workplace / "input.txt"
        with inputFile.open("w") as fp:
            fp.write(
                "\n".join(
                    ['[System]', '-- specify system name', 'Name: {}'.format("acts" + str(strength)), '',
                     '[Parameter]', '-- general syntax is parameter_name(type): value1, value2...\n'])
            )
            # write parameter ids
            for paramName, domain in domain_map.items():
                fp.write("{}(int):{}\n".format(self.getId(paramName, paramNames),
                                               ",".join([str(i) for i in range(len(domain))])))

            fp.write("\n")
            # write constraints
            if len(constraints) > 0:
                fp.write("[Constraint]\n")
                for c in constraints:
                    [fp.write(ts + "\n") for ts in self.transformConstraint(domain_map, paramNames, c)]

        return inputFile

    def callActs(self, strength: int, inputFile) -> Path:
        outputFile = self._workplace / "output.txt"
        jarPath = Path(self.jar)
        algorithm = "ipog"

        # acts 的文件路径不可以以"\"作为分割符，会被直接忽略，"\\"需要加上repr，使得"\\"仍然是"\\".
        command = r'java -Dalgo={0} -Ddoi={1} -Doutput=csv -jar {2} {3} {4}'.format(algorithm, str(strength),
                                                                                    str(jarPath),
                                                                                    str(inputFile),
                                                                                    str(outputFile))
        stdout, stderr = subprocess.Popen(shlex.split(command, posix=False), stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE).communicate()
        encoding = chardet.detect(stdout)["encoding"]
        stdout.decode(encoding)
        return outputFile

    def parseOutput(self, outputFile: Path, domain_map, paramNames):
        with outputFile.open("r") as fp:
            lines = [line.strip("\n") for line in fp.readlines() if "#" not in line and len(line.strip("\n")) > 0]
        paramNames = [self.getName(paramId, paramNames) for paramId in lines[0].strip("\n").split(",")]
        coverArray: List[Dict[str, Tuple[ValueType, Union[str, int, float, list, dict]]]] = list()
        for line in lines[1:]:
            valueDict = dict()
            valueIndexList = line.strip("\n").split(",")
            for i, valueIndex in enumerate(valueIndexList):
                valueDict[paramNames[i]] = domain_map[paramNames[i]][int(valueIndex)]
            coverArray.append(valueDict)

        return coverArray

    def process(self, domain_map, constraints: List[Constraint], strength: int):
        strength = min(strength, len(domain_map.keys()))
        paramNames = list(domain_map.keys())
        inputFile = self.writeInput(domain_map, paramNames, constraints, strength)
        outputFile = self.callActs(strength, inputFile)
        return self.parseOutput(outputFile, domain_map, paramNames)


class Executor:
    def __init__(self, queryAuth, headerAuth, manager):
        self._auth = None if len(queryAuth) == 0 and len(headerAuth) == 0 else Auth(headerAuth, queryAuth)
        self._manager = manager

    def process(self, operation, ca_item, previous_responses) -> Tuple[int, object]:
        """
        Executor的任务只有发送请求，不处理CA相关的东西
        @param operation: the target operation
        @param ca_item: assignment
        @param previous_responses: the chain
        @return: status code and response info
        """
        self.setParamValue(operation, ca_item)
        kwargs = self.assemble(operation, previous_responses)
        return self.send(operation, **kwargs)

    @staticmethod
    def assemble(operation, responses) -> dict:
        url = operation.url
        headers = {
            'Content-Type': 'application/json',
            'user-agent': 'my-app/0.0.1'
        }
        params = dict()
        files = dict()
        formData = dict()
        body = dict()

        for p in operation.parameterList:
            value = p.printableValue(responses)
            if value is None:
                if p.loc is Loc.Path:
                    url = url.replace("{" + p.name + "}", str("abc"))
                # assert p.loc is not Loc.Path, "{}:{}".format(p.name, p.loc.value)
            else:
                if p.type is DataType.File:
                    files = value
                elif p.loc is Loc.Path:
                    assert p.name != "" and p.name is not None
                    url = url.replace("{" + p.name + "}", str(value))
                elif p.loc is Loc.Query:
                    params[p.name] = value
                elif p.loc is Loc.Header:
                    headers[p.name] = value
                elif p.loc is Loc.FormData:
                    if isinstance(value, dict):
                        formData.update(value)
                    else:
                        formData[p.name] = value
                elif p.loc is Loc.Body:
                    if isinstance(value, dict):
                        body.update(value)
                    else:
                        body[p.name] = value
                else:
                    raise Exception("unexpected Param Loc Type: {}".format(p.name))

        kwargs = dict()
        kwargs["url"] = url
        kwargs["headers"] = headers
        if len(params) > 0:
            kwargs["params"] = params
        if len(files) > 0:
            kwargs["files"] = files
        if len(formData) > 0:
            kwargs["data"] = formData
        if len(body) > 0:
            kwargs["data"] = json.dumps(body)
        return kwargs

    @staticmethod
    def setParamValue(operation, case):
        # parameters: List[AbstractParam] = self._operation.genDomain(dict(), dict())
        for p in operation.parameterList:
            p.value = p.getValueDto(case)

    def send(self, operation, **kwargs) -> Tuple[int, Union[str, dict, None]]:
        self._manager.register_request()

        # for k, v in kwargs.items():
        #     logger.debug("{}: {}", k, v)

        try:
            feedback = getattr(requests, operation.method.value.lower())(**kwargs, timeout=50,
                                                                         auth=self._auth)
        except TypeError:
            raise Exception("request type error: {}".format(operation.method.value.lower()))
        except requests.exceptions.Timeout:
            return 700, "timeout"
        except requests.exceptions.TooManyRedirects:
            raise Exception("bad url, try a different one\n url: {}".format(kwargs.get("url")))
        except requests.exceptions.RequestException:
            feedback = None

        if feedback is None:
            logger.debug("status code: {}", 600)
            return 600, None
        try:
            # logger.debug("status code: {}", feedback.status_code)
            # logger.debug(feedback.json())
            return feedback.status_code, feedback.json()
        except json.JSONDecodeError:
            return feedback.status_code, feedback.text


class Auth:
    def __init__(self, headerAuth, queryAuth):
        self.headerAuth = headerAuth
        self.queryAuth = queryAuth

    def __call__(self, r):
        for key, token in self.headerAuth.items():
            r.headers[key] = token
        for key, token in self.queryAuth.items():
            r.params[key] = token
        return r


@dataclass(frozen=True)
class Value:
    val: object = None
    generator: ValueType = ValueType.NULL
    type: DataType = DataType.NULL


class RuntimeInfoManager:
    def __init__(self):
        self._num_of_requests = 0

        self._ok_value_dict: Dict[str, List[Tuple[ValueType, object]]] = defaultdict(list)
        self._reused_essential_seq_dict: Dict[Tuple[Operation], List[Dict[str, Value]]] = defaultdict(list)
        self._reused_all_p_seq_dict: dict = defaultdict(list)
        self._response_chains: List[Dict[str, object]] = [dict()]
        self._bug_list: list = list()
        self._success_sequence: set = set()
        self._unresolved_params: Set[Tuple[Operation, str]] = set()

    def essential_executed(self, operations: Tuple[Operation]):
        return operations in self._reused_essential_seq_dict.keys()

    def all_executed(self, operations: Tuple[Operation]):
        return operations in self._reused_all_p_seq_dict.keys()

    def get_reused_with_essential_p(self, operations: Tuple[Operation]):
        reused_case = self._reused_essential_seq_dict.get(operations, list())
        if len(reused_case) > 0:
            return [{p: Value(v.val, ValueType.Reused, v.type) for p, v in case.items()} for case in reused_case]
        return []

    def get_reused_with_all_p(self, operations: Tuple[Operation]):
        reused_case = self._reused_all_p_seq_dict.get(operations, list())
        if len(reused_case) > 0:
            return [{p: Value(v.val, ValueType.Reused, v.type) for p, v in case.items()} for case in reused_case]
        return []

    def get_ok_value_dict(self):
        return self._ok_value_dict

    def is_unresolved(self, p_name):
        return p_name in self._unresolved_params

    def register_request(self):
        self._num_of_requests += 1

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
                value_list = [v for _, v in lst]
                if len(lst) < 10 and value[1] not in value_list:
                    lst.append(value)
                else:
                    type_set = {t for t, _ in lst}
                    if value[0] not in type_set:
                        lst.append(value)

    def save_chain(self, chain, operation, response):
        new_chain = chain.copy()
        new_chain[operation] = response
        self._response_chains.append(new_chain)
        if len(self._response_chains) > 10:
            self._response_chains.pop(0)

    def save_id_count(self, operation, response, id_counter):
        if isinstance(response, dict):
            iid = response.get("id")
            try:
                id_counter.append((iid, operation.url))
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

    def save_bug(self, operation, case, sc, response, chain, data_path):
        op_str_set = {d.get("method") + d.get("url") + str(d.get("statusCode")) for d in self._bug_list}
        if operation.method + operation.url + str(sc) in op_str_set:
            return
        bug_info = {
            "url": operation.url,
            "method": operation.method,
            "parameters": {paramName: (vt.value, v) for paramName, (vt, v) in case.items()},
            "statusCode": sc,
            "response": response,
            "responseChain": chain
        }
        self._bug_list.append(bug_info)

        folder = Path(data_path) / "bug/"
        if not folder.exists():
            folder.mkdir(parents=True)
        bugFile = folder / "bug_{}.json".format(str(len(op_str_set)))
        with bugFile.open("w") as fp:
            json.dump(bug_info, fp)

    def save_success_seq(self, url_tuple):
        self._success_sequence.add(url_tuple)

    def get_chains(self, maxChainItems):
        sortedList = sorted(self._response_chains, key=lambda c: len(c.keys()), reverse=True)
        return sortedList[:maxChainItems] if maxChainItems < len(sortedList) else sortedList


class CA:
    # value used in success http calls. key: operation._repr_+paramName
    # okValueDict: Dict[str, List[Tuple[ValueType, object]]] = defaultdict(list)
    # success http call sequence. key: url, value: last operation's parameters and values
    # reuseEssentialSeqDict: Dict[
    #     Tuple[str], List[Dict[str, Tuple[ValueType, Union[str, int, float, list, dict]]]]] = defaultdict(list)
    # reuseAllSeqDict: Dict[Tuple[str], List[Dict[str, Tuple[ValueType, object]]]] = defaultdict(list)
    # bug: {url: , method: , parameters: , statusCode: , response: , sequence}
    # bugList: List[Dict[str, Union[str, dict, int, list]]] = list()
    # seq actually tested, return 20X or 500
    # successSet: Set = set()

    def __init__(self, data_path, acts_jar, a_strength, e_strength, **kwargs):

        # response chain
        self._maxChainItems = 3
        # idCount: delete created resource
        self._id_counter: List[(int, str)] = list()

        self._aStrength = a_strength  # cover strength for all parameters
        self._eStrength = e_strength  # cover strength for essential parameters

        ######### refactored code ###########
        self._manager = RuntimeInfoManager()
        self._acts = ACTS(data_path, acts_jar)
        self._executor = Executor(kwargs.get("query_auth"), kwargs.get("header_auth"), self._manager)

        self._data_path = data_path
        self._start_time = time.time()

    def _select_response_chains(self, response_chains):
        """get _maxChainItems longest chains"""
        sortedList = sorted(response_chains, key=lambda c: len(c.keys()), reverse=True)
        return sortedList[:self._maxChainItems] if self._maxChainItems < len(sortedList) else sortedList

    def _executes(self, operation, ca, chain, url_tuple, is_essential=True):
        response_list: List[(int, object)] = []
        for case in ca:
            status_code, response = self._executor.process(operation, case, chain)
            response_list.append((status_code, response))

        self._handle_feedback(url_tuple, operation, response_list, chain, ca, is_essential)

    def _handle_feedback(self, url_tuple, operation, response_list, chain, ca, is_essential):
        is_success = False
        for index, (sc, response) in enumerate(response_list):
            if sc < 300:
                self._manager.save_reuse(url_tuple, is_essential, ca[index])
                self._manager.save_ok_value(ca[index])
                self._manager.save_chain(chain, operation, response)
                is_success = True
            if operation.method is Method.POST and sc < 300:
                self._manager.save_id_count(operation, response, self._id_counter)
            if sc in range(500, 600):
                self._manager.save_bug(operation, ca[index], sc, response, chain, self._data_path)
                is_success = True
        if is_success:
            self._manager.save_success_seq(url_tuple)

    def _handle_one_operation(self, index, operation: Operation, chain: dict, sequence):
        self._reset_constraints(operation, operation.parameterList)
        success_url_tuple = tuple([op for op in sequence[:index] if op in chain.keys()] + [operation])

        e_ca = self._handle_essential_params(operation, sequence[:index], chain)
        logger.info(f"{index + 1}-th operation essential parameters covering array size: {len(e_ca)}, "
                    f"parameters: {len(e_ca[0])}, constraints: {len(operation.constraints)}")

        self._executes(operation, e_ca, chain, success_url_tuple)

        if all([p.isEssential for p in operation.parameterList]):
            return

        # todo history is not None, add return values of executes
        a_ca = self._handle_all_params(operation, sequence[:index], chain, history=None)
        logger.info(f"{index + 1}-th operation all parameters covering array size: {len(a_ca)}, "
                    f"parameters: {len(a_ca[0])}, constraints: {len(operation.constraints)}")

        self._executes(operation, a_ca, chain, False)

    def _handle_essential_params(self, operation, exec_ops, chain):
        """

        :param operation:
        :param exec_ops: sequence[:i]
        :param chain:
        :return:
        """
        reused_case = self._manager.get_reused_with_essential_p(tuple(exec_ops + [operation]))
        if len(reused_case) > 0:
            # 执行过
            logger.debug("        use reuseSeq info: {}, parameters: {}", len(reused_case), len(reused_case[0].keys()))
            return reused_case

        return self._cover_params(operation, operation.parameterList, operation.constraints, chain)

    def _handle_all_params(self, operation, exec_ops, chain, history):
        reused_case = self._manager.get_reused_with_all_p(tuple(exec_ops + [operation]))
        if len(reused_case) > 0:
            # 执行过
            logger.debug("        use reuseSeq info: {}, parameters: {}", len(reused_case), len(reused_case[0].keys()))
            return reused_case

        return self._cover_params(operation, operation.parameterList, operation.constraints, chain, history)

    def _cover_params(self, operation, parameters, constraints, chain, history: List[dict] = None):
        """
        generate domain for each parameter of the current operation
        @param history: executed essential params
        @param operation: the target operation
        @param parameters: parameter list
        @param constraints: the constraints among parameters
        @param chain: a response chain
        @return: the parameters and their domains
        """

        if history is None:
            history = []
        essential_p_list = list(filter(lambda p: p.isEssential, parameters))
        if len(essential_p_list) == 0:
            return []

        domain_map = defaultdict(list)
        for root_p in essential_p_list:
            p_with_children = root_p.genDomain(operation.__repr__(), chain, self._manager.get_ok_value_dict())
            for p in p_with_children:
                if not self._manager.is_unresolved(operation.__repr__() + p.name):
                    domain_map[p.getGlobalName()] = p.domain

        if history is not None and len(history) > 0:
            new_domain_map = {
                "successEssentialCases": [Value(v, ValueType.Null, DataType.Int32) for v in range(len(history))]}

            for p in domain_map.keys():
                if p not in history[0].keys():
                    new_domain_map[p] = domain_map.get(p)

            for c in operation.constraints:
                for p in c.paramNames:
                    if self._manager.is_unresolved(p):
                        return dict()

            domain_map = new_domain_map

        for p, v in domain_map.items():
            logger.debug(f"            {p}: {len(v)} - {v}")

        return self._call_acts(domain_map, constraints, self._eStrength)

    def _call_acts(self, domain_map, constraints, strength):
        try:
            self._acts.process(domain_map, constraints, strength)
        except Exception:
            logger.warning("call acts wrong")


    @staticmethod
    def _timeout(start_time, budget):
        return time.time() - start_time > budget

    @staticmethod
    def _reset_constraints(operation: Operation, parameters: List[AbstractParam]):
        constraint_processor = Processor(parameters)
        constraints: List[Constraint] = constraint_processor.parse()
        operation.set_constraints(constraints)

    def clear_up(self):
        for iid, url in self._id_counter:
            resource_id = url.rstrip("/") + "/" + str(iid)
            try:
                requests.delete(url=resource_id, auth=Auth())
            except Exception:
                continue

    def handle(self, sequence, budget):
        for index, operation in enumerate(sequence):
            logger.debug("{}-th operation: {}*{}", index + 1, operation.method.value, operation.url)
            chainList = self._manager.get_chains(self._maxChainItems)
            while len(chainList):
                if self._timeout(self._start_time, budget):
                    return False
                chain = chainList.pop(0)
                self._handle_one_operation(index, operation, chain, sequence)
