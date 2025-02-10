import abc
import base64
import datetime
import os
import random
import re
import string
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, List, Union, Tuple

import Levenshtein

from src.keywords import DataType


class ValueType(Enum):
    Enum = "enum"
    Default = "default"
    Example = "example"
    Random = "random"
    Dynamic = "dynamic"
    Reused = "Reused"
    NULL = "Null"


@dataclass(frozen=True)
class Value:
    val: object = None
    generator: ValueType = ValueType.NULL
    type: DataType = DataType.NULL


class AbstractFactor(metaclass=abc.ABCMeta):
    value_nums = 2
    """
    Abstract class for Factors
    """

    def __init__(self, name: str):
        self.name: str = name
        self.description: Optional[str] = None

        # Set the required flag to true
        self.required: bool = False
        self.parent: Optional[AbstractFactor] = None

        self._examples: list = []
        self._default: Optional[Any] = None
        self.format = None
        self.is_constraint = False
        self.domain: list[Value] = list()
        self.isReuse: bool = False

        self.value = None

    @staticmethod
    def get_ref(ref: str, definitions: dict):
        """get definition with the ref name"""
        return definitions.get(ref.split("/")[-1], {})

    @property
    def is_essential(self):
        return self.is_constraint or self.required

    def see_all_factors(self) -> List:
        """get factors itself and its children"""
        if self.name is None or self.name == "":
            return list()
        else:
            return [self]

    def gen_domain(self):
        pass

    def gen_path(self, op, chain, manager):
        self.domain.clear()
        dynamic_values = list()
        response_value = list()
        op_set = chain.keys()
        high_weight, low_weight = AbstractFactor._analyse_url_relation(op, op_set, self.name)
        for predecessor in high_weight:
            response = chain.get(predecessor)
            similarity_max = 0
            path_depth_minimum = 10
            right_path = None
            right_value = None
            for path, similarity, value in AbstractFactor.find_dynamic(self.name, response):
                if similarity > similarity_max:
                    right_path = path
                    path_depth_minimum = len(path)
                    similarity_max = similarity
                    right_value = value
                elif similarity == similarity_max:
                    if len(path) < path_depth_minimum:
                        right_path = path
                        path_depth_minimum = len(path)
                        right_value = value
            if similarity_max > 0 and right_value not in response_value:
                dynamic_values.append((predecessor, right_path))
        if len(dynamic_values) > 0:
            if len(dynamic_values) < self.value_nums:
                self.gen_domain()
            for v in dynamic_values:
                self.domain.append(Value(v, ValueType.Dynamic, DataType.NULL))
        else:
            self.gen_domain()

    @staticmethod
    def _analyse_url_relation(op, op_set, param_name):
        high_weight = list()
        low_weight = list()
        url = op.path.__repr__()
        for candidate in op_set:
            other_url = candidate.path.__repr__()
            if other_url.strip("/") == url.split("{" + param_name + "}")[0].strip("/"):
                high_weight.append(candidate)
            elif other_url.strip("/") == url.split("{" + param_name + "}")[0].strip("/") + "/{" + param_name + "}":
                high_weight.append(candidate)
            else:
                low_weight.insert(0, candidate)
        return high_weight, low_weight

    @staticmethod
    def find_dynamic(paramName, response, path=None):
        if re.search(r"[-_]?id[-_]?", paramName) is not None:
            name = "id"
        if path is None:
            path = []
        if isinstance(response, list):
            local_path = path[:]
            if response:
                for result in AbstractFactor.find_dynamic(paramName, response[0], local_path):
                    yield result
        elif isinstance(response, dict):
            for k, v in response.items():
                local_path = path[:]
                similarity = AbstractFactor.match(paramName, k)
                if similarity > 0.9:
                    local_path.append(k)
                    yield local_path, similarity, v
                elif isinstance(v, (list, dict)):
                    local_path.append(k)
                    for result in AbstractFactor.find_dynamic(paramName, v, local_path[:]):
                        yield result
        else:
            pass

    @staticmethod
    def match(str_a, str_b):
        str_a = "".join(c for c in str_a if c.isalnum())
        str_b = "".join(c for c in str_b if c.isalnum())
        distance = Levenshtein.distance(str_a.lower(), str_b.lower())
        length_total = len(str_a) + len(str_b)
        return round((length_total - distance) / length_total, 2)

    def add_domain_to_map(self, domain_map: dict):
        if len(self.domain) > 0:
            domain_map[self.get_global_name] = self.domain
        return domain_map

    def set_value(self, case, is_reuse=False):
        self.value = None
        for name, value in case.items():
            if name == self.get_global_name:
                if not is_reuse:
                    self.value = value
                else:
                    self.value = self.mutate_value(value)

    def printable_value(self, response=None):
        if self.value is not None and self.value.generator is ValueType.Dynamic:
            if response is None or len(response) == 0:
                value = "1"
            else:
                op_str, path = self.value.val
                response = response.get(op_str)
                value = self._assemble_dynamic(path, response)
            self.value = Value(value, ValueType.Dynamic, DataType.NULL)
        if self.value is not None:
            if self.value.val == "blank":
                return ""
            else:
                return self.value.val
        else:
            return None

    @staticmethod
    def _assemble_dynamic(path, response):
        value = response
        for p in path:
            if isinstance(value, list):
                try:
                    value = value[0]
                except IndexError:
                    return None
            try:
                value = value.get(p)
            except (AttributeError, TypeError):
                return None
            else:
                if value is None:
                    return None
        return value

    def get_leaves(self) -> Tuple:
        """
        Get all leaves of the factor tree,
        excluding arrays and objects themselves.
        """
        return self,

    @staticmethod
    def mutate_value(value: Value):
        if value.val is not None and value.val != '' and value.generator is not ValueType.Dynamic:
            if value.type == DataType.String:
                new_value = Value(value.val + "1", value.generator, value.type)
            elif value.type == DataType.Integer:
                new_value = Value(int(value.val) + 1, value.generator, value.type)
            elif value.type == DataType.Number:
                new_value = Value(float(value.val) + 1, value.generator, value.type)
            else:
                new_value = value
        else:
            new_value = value
        return new_value

    def __repr__(self):
        return self.get_global_name

    @property
    def get_global_name(self):
        if self.parent is not None:
            return f"{self.parent.get_global_name}.{self.name}"
        else:
            return self.name

    def __hash__(self):
        return hash(self.get_global_name)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.get_global_name == other.get_global_name:
            return True
        else:
            return False

    def set_description(self, text: str):
        if text is None:
            return
        if text.startswith("'"):
            text = text[1:]
        if text.endswith("'"):
            text = text[:-1]
        if text.startswith('"'):
            text = text[1:]
        if text.endswith('"'):
            text = text[:-1]
        text = text.strip()
        if len(text) == 0:
            return
        self.description = text

    def set_example(self, example):
        parsed_example = self._spilt_example(example)
        if parsed_example is not None:
            for e in parsed_example:
                if e not in self._examples:
                    self._examples.append(e)

    @property
    def all_examples(self):
        return self._examples

    @staticmethod
    def _spilt_example(example) -> Union[list, None]:
        if example is None:
            return None
        if isinstance(example, list):
            return example
        if isinstance(example, dict):
            raise ValueError("Example cannot be a dict")
        return [example]

    def set_default(self, default_value):
        if default_value is not None:
            self._default = default_value


class StringFactor(AbstractFactor):
    def __init__(self, name: str, format: str = None, min_length: int = 0, max_length: int = 100):
        super().__init__(name)
        self.type = DataType.String
        self.format = format
        self.minLength = min_length
        self.maxLength = max_length

    def gen_domain(self):
        self.domain.clear()
        if self._default is not None:
            self.domain.append(Value(self._default, ValueType.Default, DataType.String))
        if len(self.all_examples) > 0:
            for example in self.all_examples:
                self.domain.append(Value(example, ValueType.Example, DataType.String))
        if len(self.domain) < self.value_nums:
            while len(self.domain) < self.value_nums:
                if self.format == "date":
                    random_date = datetime.date.fromtimestamp(
                        random.randint(0, int(datetime.datetime.now().timestamp()))).strftime('%Y-%m-%d')
                    self.domain.append(Value(str(random_date), ValueType.Random, DataType.String))
                elif self.format == "date-time":
                    random_datetime = datetime.datetime.fromtimestamp(
                        random.randint(0, int(datetime.datetime.now().timestamp())))
                    self.domain.append(Value(str(random_datetime), ValueType.Random, DataType.String))
                elif self.format == "password":
                    random_password_length = random.randint(5, 10)
                    characters = string.ascii_letters + string.digits + string.punctuation
                    password = ''.join(random.choice(characters) for _ in range(random_password_length))
                    self.domain.append(Value(password, ValueType.Random, DataType.String))
                elif self.format == "byte":
                    random_byte_length = random.randint(1, 10)
                    byte_str = base64.b64encode(os.urandom(random_byte_length)).decode('utf-8')
                    self.domain.append(Value(str(byte_str), ValueType.Random, DataType.String))
                elif self.format == "binary":
                    random_binary_length = random.randint(1, 10)
                    binary_str = ''.join(random.choice(['0', '1']) for _ in range(random_binary_length))
                    self.domain.append(Value(binary_str, ValueType.Random, DataType.String))
                else:
                    characters1 = string.ascii_letters
                    characters2 = string.ascii_letters + string.digits + string.punctuation
                    length = random.randint(self.minLength, self.maxLength)
                    random_string1 = ''.join(random.choice(characters1) for _ in range(length))
                    random_string2 = ''.join(random.choice(characters2) for _ in range(length))
                    self.domain.append(Value(random_string1, ValueType.Random, DataType.String))
                    self.domain.append(Value(random_string2, ValueType.Random, DataType.String))
            self.domain.append(Value("blank", ValueType.Default, DataType.String))

        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.String))


class IntegerFactor(AbstractFactor):
    def __init__(self, name: str, minimum: int = None, maximum: int = None):
        super().__init__(name)
        self.type = DataType.Integer
        self.minimum = minimum
        self.maximum = maximum

    def gen_domain(self):
        self.domain.clear()
        if self._default is not None:
            self.domain.append(Value(self._default, ValueType.Default, DataType.Integer))
        if len(self.all_examples) > 0:
            for example in self.all_examples:
                self.domain.append(Value(example, ValueType.Example, DataType.Integer))
        if len(self.domain) < self.value_nums:
            while len(self.domain) < self.value_nums:
                if self.minimum is not None and self.maximum is not None:
                    random_int = random.randint(self.minimum, self.maximum)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Integer))
                elif self.minimum is not None:
                    random_int = random.randint(self.minimum, self.minimum + 10000)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Integer))
                elif self.maximum is not None:
                    random_int = random.randint(self.maximum - 10000, self.maximum)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Integer))
                else:
                    random_int = random.randint(-10000, 10000)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Integer))
        # value_list = [v.val for v in self.domain]
        # if 0 not in value_list:
        #     self.domain.append(Value(0, ValueType.Default, DataType.Integer))
        # if 1 not in value_list:
        #     self.domain.append(Value(1, ValueType.Default, DataType.Integer))
        # if -1 not in value_list:
        #     self.domain.append(Value(-1, ValueType.Default, DataType.Integer))
        # if 2 not in value_list:
        #     self.domain.append(Value(2, ValueType.Default, DataType.Integer))
        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.Integer))


class NumberFactor(AbstractFactor):
    def __init__(self, name: str, minimum: int = None, maximum: int = None):
        super().__init__(name)
        self.type = DataType.Number
        self.minimum = minimum
        self.maximum = maximum

    def gen_domain(self):
        self.domain.clear()
        if self._default is not None:
            self.domain.append(Value(self._default, ValueType.Default, DataType.Number))
        if len(self.all_examples) > 0:
            for example in self.all_examples:
                self.domain.append(Value(example, ValueType.Example, DataType.Number))
        if len(self.domain) < self.value_nums:
            while len(self.domain) < self.value_nums:
                if self.minimum is not None and self.maximum is not None:
                    random_int = random.uniform(self.minimum, self.maximum)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Number))
                elif self.minimum is not None:
                    random_int = random.uniform(self.minimum, self.minimum + 10000)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Number))
                elif self.maximum is not None:
                    random_int = random.uniform(self.maximum - 10000, self.maximum)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Number))
                else:
                    random_int = random.uniform(-1000, 1000)
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Number))
        # value_list = [int(v.val) for v in self.domain]
        # if 0 not in value_list:
        #     self.domain.append(Value(0.0, ValueType.Default, DataType.Integer))
        # if 1 not in value_list:
        #     self.domain.append(Value(1.0, ValueType.Default, DataType.Integer))
        # if -1 not in value_list:
        #     self.domain.append(Value(-1.0, ValueType.Default, DataType.Integer))
        # if 2 not in value_list:
        #     self.domain.append(Value(2.0, ValueType.Default, DataType.Integer))
        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.Number))


class BooleanFactor(AbstractFactor):
    def __init__(self, name: str):
        super().__init__(name)
        self.type = DataType.Bool

    def gen_domain(self):
        self.domain.clear()
        self.domain.append(Value(True, ValueType.Enum, DataType.Bool))
        self.domain.append(Value(False, ValueType.Enum, DataType.Bool))
        if not self.required:
            self.domain.append(Value(None, ValueType.Enum, DataType.Bool))


class ObjectFactor(AbstractFactor):
    def __init__(self, name: str):
        super().__init__(name)
        self.type = DataType.Object

        self.properties: List[AbstractFactor] = []

    def add_property(self, p: AbstractFactor):
        self.properties.append(p)
        p.parent = self

    def gen_domain(self):
        self.domain.clear()
        for p in self.properties:
            p.gen_domain()

    def add_domain_to_map(self, domain_map: dict):
        for p in self.properties:
            p.add_domain_to_map(domain_map)
        return domain_map

    def set_value(self, case, is_reuse=False):
        self.value = None
        for p in self.properties:
            p.set_value(case, is_reuse)
        property_not_none = [p for p in self.properties if p.printable_value() is not None]
        if len(property_not_none) > 0:
            self.value = {}
            for p in property_not_none:
                self.value[p.name] = p.printable_value()

    def get_leaves(self) -> Tuple:
        leaves = []
        for p in self.properties:
            leaves.extend(p.get_leaves())
        return tuple(leaves)

    def printable_value(self, response=None):
        if self.value is None:
            return None
        return self.value


class ArrayFactor(AbstractFactor):
    def __init__(self, name: str):
        super().__init__(name)
        self.type = DataType.Array
        self.item: Optional[AbstractFactor] = None

    def set_item(self, item: AbstractFactor):
        self.item = item
        self.item.parent = self

    def gen_domain(self):
        self.domain.clear()
        if self.item is not None:
            self.item.gen_domain()

    def add_domain_to_map(self, domain_map: dict):
        if self.item is not None:
            self.item.add_domain_to_map(domain_map)
        return domain_map

    def set_value(self, case, is_reuse=False):
        self.value = None
        self.item.set_value(case, is_reuse)
        if self.item.printable_value() is not None:
            self.value = []
            self.value.append(self.item.printable_value())

    def get_leaves(self) -> Tuple:
        return self.item.get_leaves()

    def printable_value(self, response=None):
        if self.value is None:
            return None
        return self.value


class EnumFactor(AbstractFactor):
    def __init__(self, name: str, enum_value: list):
        super().__init__(name)
        self.enum_value = enum_value

    def gen_domain(self):
        self.domain.clear()
        for e in self.enum_value:
            self.domain.append(Value(e, ValueType.Enum, DataType.NULL))
        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.String))
