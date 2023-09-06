import re
import abc
import base64
import random
import string
import Levenshtein
from enum import Enum
from datetime import datetime, timedelta
from typing import Tuple, List, Union, Dict
from src.Dto.keywords import Loc, ParamKey, DataType, DocKey
from src.Exception.exceptions import UnsupportedError


def buildParam(info: dict, definitions: dict, specifiedName: str = None):
    buildInfo = {
        "specifiedName": info.get(ParamKey.NAME, "") if specifiedName is None else specifiedName,
        "paramType": DataType(info.get(ParamKey.TYPE, DataType.NULL.value)),
        "paramFormat": DataType(info.get(ParamKey.FORMAT, DataType.NULL.value).replace("-", "")),
        "default": [info.get(ParamKey.DEFAULT)] if info.get(ParamKey.DEFAULT) is not None else list(),
        "loc": Loc(info.get(ParamKey.LOCATION, Loc.NULL.value)),
        "required": info.get(ParamKey.REQUIRED, False),
        "description": info.get(ParamKey.DESCRIPTION, "")
    }
    paramEnum = info.get(ParamKey.ENUM, None)

    if buildInfo["paramType"] is DataType.NULL:
        if ParamKey.SCHEMA in info.keys():
            extraInfo = AbstractParam.getRef(info.get(ParamKey.SCHEMA, None).get(DocKey.REF_SIGN, None), definitions)
        elif DocKey.REF_SIGN in info.keys():
            extraInfo = AbstractParam.getRef(info.get(DocKey.REF_SIGN, None), definitions)
        elif DocKey.ALL_OF in info.keys() or DocKey.ANY_OF in info.keys() or DocKey.ONE_OF in info.keys() or DocKey.ADDITIONAL_PROPERTIES in info.keys():
            return None
        else:
            raise UnsupportedError(info)
        extraInfo.update(info)
        return buildParam(extraInfo, definitions, buildInfo.get("specifiedName"))
    elif paramEnum is not None:
        buildInfo["enum"] = paramEnum
        return EnumParam(**buildInfo)
    elif buildInfo["paramType"] in [DataType.Double, DataType.Integer, DataType.Number, DataType.Int32, DataType.Int64,
                                    DataType.Float, DataType.Long]:
        buildInfo["maximum"] = info.get(ParamKey.MAXIMUM, 100)
        buildInfo["minimum"] = info.get(ParamKey.MINIMUM, 0)
        buildInfo["exclusiveMinimum"] = info.get(ParamKey.EXCLUSIVEMINIMUM, False)
        buildInfo["exclusiveMaxiMum"] = info.get(ParamKey.EXCLUSIVEMAXIMUM, False)
        return NumberParam(**buildInfo)
    elif buildInfo["paramType"] is DataType.Array:
        buildInfo["items"] = info.get(ParamKey.ITEMS, {})
        buildInfo["maxItems"] = info.get(ParamKey.MAXITEMS, 3)
        buildInfo["minItems"] = info.get(ParamKey.MINITEMS, 1)
        buildInfo["unique"] = info.get(ParamKey.UNIQUEITEMS, False)
        return ArrayParam.buildArray(buildInfo, definitions)
    elif buildInfo["paramType"] is DataType.Bool:
        return BoolParam(**buildInfo)
    elif buildInfo["paramType"] is DataType.String:
        if buildInfo["paramFormat"] in [DataType.NULL, DataType.Binary, DataType.Byte]:
            buildInfo["maxLength"] = info.get(ParamKey.MAXLENGTH, 20)
            buildInfo["minLength"] = info.get(ParamKey.MINLENGTH, 1)
            return StringParam(**buildInfo)
        elif buildInfo["paramFormat"] is DataType.Date:
            return Date(**buildInfo)
        elif buildInfo["paramFormat"] is DataType.DateTime:
            return DateTime(**buildInfo)
        elif buildInfo["paramFormat"] is DataType.File:
            return FileParam(**buildInfo)
        elif buildInfo["paramFormat"] is DataType.UUID:
            return UuidParam(**buildInfo)
        else:
            raise UnsupportedError(info.__str__() + " is not taken into consideration")
    elif buildInfo["paramType"] is DataType.File:
        return FileParam(**buildInfo)
    elif buildInfo["paramType"] is DataType.Object:
        buildInfo["allInfo"] = info
        buildInfo["required"] = info.get("required", [])
        return ObjectParam.buildObject(buildInfo, definitions)
    else:
        raise UnsupportedError(info.__str__() + " is not taken into consideration")


class ValueType(Enum):
    Enum = "enum"
    Default = "default"
    Example = "example"
    Random = "random"
    Dynamic = "dynamic"
    NULL = "Null"


class Example:
    members = set()

    def __init__(self, paramStr: str, value):
        self.parameterStr: str = paramStr

        self.value = value

        if self.value not in [None, ""]:
            Example.members.add(self)

    @staticmethod
    def findExample(parameterStr: str):
        allValues = list()
        for example in Example.members:
            if example.parameterStr == parameterStr:
                allValues.append(example.value)
        return allValues

    def __hash__(self):
        return hash(str(self.parameterStr) + str(self.value))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.parameterStr == other.parameterStr and self.value == other.value


class Fuzzer:
    @staticmethod
    def delete_random_character(s, *args):
        if s == "":
            return s
        pos = random.randint(0, len(s) - 1)
        return s[:pos] + s[pos + 1:]

    @staticmethod
    def insert_random_character(s, t):
        pos = random.randint(0, len(s))
        # random_character = chr(random.randrange(48, 127))
        # 特殊符号导致请求失败
        if t == "int":
            random_character = chr(random.choice([i for i in range(48, 58)]))
        elif t == "string":
            random_character = chr(random.choice([i for i in range(65, 91)] + [i for i in range(97, 123)]))
        else:
            random_character = chr(
                random.choice([i for i in range(48, 58)] + [i for i in range(65, 91)] + [i for i in range(97, 123)]))
        return s[:pos] + random_character + s[pos:]

    @staticmethod
    def flip_random_character(s, *args):
        if s == "":
            return s
        pos = random.randint(0, len(s) - 1)
        c = s[pos]
        bit = 1 << random.randint(0, 6)
        new_c = chr(ord(c) ^ bit)
        return s[:pos] + new_c + s[pos + 1:]

    @staticmethod
    def mutate_str(s, t):
        mutators = [
            Fuzzer.delete_random_character,
            Fuzzer.insert_random_character
            # Fuzzer.flip_random_character
        ]
        mutator = random.choice(mutators)
        return mutator(s, t)

    @staticmethod
    def mutate(v, r=2):
        if isinstance(v, int):
            return [random.randint(1, 9) for _ in range(r)]
        elif isinstance(v, float):
            return [round(random.uniform(0, 100), 2) for _ in range(r)]
        else:
            t_set = ["string", "int"]
            return [Fuzzer.mutate_str(str(v), t_set[i % 2]) for i in range(r)]


class AbstractParam(metaclass=abc.ABCMeta):
    randomCount = 3

    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str):
        self.name: str = specifiedName

        # default value
        self.default: list = default
        # in which part of HTTP request
        self.loc: Loc = loc
        # required or not
        self.required: bool = required
        # parameter type
        self.type: DataType = paramType
        # parameter format
        self.format: DataType = paramFormat
        # description
        self.description: str = description

        # if involved in constraints
        self.isConstrained = False
        # domain
        self.domain: List[Tuple[ValueType, Union[str, int, float, None]]] = list()
        # self.value: Tuple[ValueType, str] = tuple()
        self.value = None
        self.isReuse: bool = False
        self.parent: AbstractParam = None

    @staticmethod
    def getRef(ref: str, definitions: dict):
        """get definition with the ref name"""
        return definitions.get(ref.split("/")[-1], {})

    @property
    def isEssential(self):
        return self.isConstrained or self.required

    def seeAllParameters(self) -> List:
        """get Parameters itself and its children"""
        if self.name is None or self.name == "":
            return list()
        else:
            return [self]

    def genDomain(self, opStr, responseChains, okValues) -> list:
        if self.isReuse:
            # parameter 是一个被执行过的，domain是使用过的，需要进行变换
            # self.genReuseDomain()
            pass
        else:
            if self.loc is Loc.Path:
                self.domain = self._getDynamicValues(opStr, responseChains)
            if len(self.domain) > 0:
                return [self]

            if len(self.default) > 0:
                self.domain = [(ValueType.Default, d) for d in self.default]
                if len(self.domain) > 0:
                    if not self.required:
                        self.domain.append((ValueType.NULL, None))
                    return [self]
            elif okValues is not None and len(okValues) > 0:
                self.domain = self._getOkValue(opStr, okValues)
                if len(self.domain) > 0:
                    if not self.required:
                        self.domain.append((ValueType.NULL, None))
                    return [self]
            else:
                pass

            exampleValues = Example.findExample(self.name)[:2]
            if len(exampleValues) == 1:
                self.domain = [(ValueType.Random, Fuzzer.mutate(exampleValues[0])[0]),
                               (ValueType.Default, exampleValues[0])]
            elif len(exampleValues) > 1:
                vTSet = (ValueType.Default, ValueType.Random)
                self.domain = [(vTSet[i % 2], e) for i, e in enumerate(exampleValues)]
            else:
                randomValue = self.genRandom()
                self.domain = [(ValueType.Random, r) for r in randomValue]

            if not self.required:
                self.domain.append((ValueType.NULL, None))
        return [self]

    def _getOkValue(self, opStr, okValues) -> List[Tuple[ValueType, Union[str, int, float, None]]]:
        paramId = opStr + self.name
        domain = list()
        for valueType, value in okValues.get(paramId, []):
            domain.append((valueType, value))
        return domain

    def _getDynamicValues(self, opStr, responseChains):
        """完全重用，需要改进"""
        assert self.loc is Loc.Path
        assert self.name != "" and self.name is not None
        dynamicValues = list()
        responseValue = list()
        opSet = responseChains.keys()
        highWeight, lowWeight = AbstractParam._analyseUrlRelation(opStr, opSet, self.name)
        for predecessor in highWeight:
            response = responseChains.get(predecessor)
            similarity_max = 0
            path_depth_minimum = 10
            right_path = None
            right_value = None
            for path, similarity, value in AbstractParam.findDynamic(self.name, response):
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
            if similarity_max > 0 and right_value not in responseValue:
                dynamicValues.append((predecessor, right_path))
        if len(dynamicValues) > 0:
            return [(ValueType.Dynamic, v) for v in dynamicValues]
        else:
            return list()

    @staticmethod
    def match(str_a, str_b):
        str_a = "".join(c for c in str_a if c.isalnum())
        str_b = "".join(c for c in str_b if c.isalnum())
        distance = Levenshtein.distance(str_a.lower(), str_b.lower())
        length_total = len(str_a) + len(str_b)
        return round((length_total - distance) / length_total, 2)

    @staticmethod
    def findDynamic(paramName, response, path=None):
        if re.search(r"[-_]?id[-_]?", paramName) is not None:
            name = "id"
        if path is None:
            path = []
        if isinstance(response, list):
            local_path = path[:]
            if response:
                for result in AbstractParam.findDynamic(paramName, response[0], local_path):
                    yield result
        elif isinstance(response, dict):
            for k, v in response.items():
                local_path = path[:]
                similarity = AbstractParam.match(paramName, k)
                if similarity > 0.9:
                    local_path.append(k)
                    yield local_path, similarity, v
                elif isinstance(v, (list, dict)):
                    local_path.append(k)
                    for result in AbstractParam.findDynamic(paramName, v, local_path[:]):
                        yield result
        else:
            pass

    @staticmethod
    def _analyseUrlRelation(opStr, opSet, paramName):
        highWeight = list()
        lowWeight = list()
        url = opStr.split("***")[-1]
        for candidate in opSet:
            otherUrl = candidate.split("***")[-1]
            if otherUrl.strip("/") == url.split("{" + paramName + "}")[0].strip("/"):
                highWeight.append(candidate)
            elif otherUrl.strip("/") == url.split("{" + paramName + "}")[0].strip("/") + "/{" + paramName + "}":
                highWeight.append(candidate)
            else:
                lowWeight.insert(0, candidate)
        return highWeight, lowWeight

    @abc.abstractmethod
    def genRandom(self) -> list:
        pass

    def printableValue(self, response):
        if len(self.value) == 0:
            return None
        valueType, value = self.value
        if valueType is ValueType.Random:
            value = Fuzzer.mutate(value, r=1)[0]
        if valueType is ValueType.Dynamic:
            opStr, path = value
            response = response.get(opStr)
            value = self._assembleDynamic(path, response)
        return value

    @staticmethod
    def _assembleDynamic(path, response):
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

    def __repr__(self):
        return self.name

    def getGlobalName(self):
        if self.parent is not None:
            return self.parent.getGlobalName() + "@" + self.name
        else:
            return self.name

    @abc.abstractmethod
    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        # object -> dict
        # array -> list
        pass


class ObjectParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str, children: List[AbstractParam]):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

        self._children: List[AbstractParam] = children
        self.value: Dict[str, Tuple[ValueType, str]] = dict()
        for child in self._children:
            child.parent = self

    @classmethod
    def buildObject(cls, info, definitions):
        childrenInfo = info.pop("allInfo")
        keywords = ["allOf", "oneOf", "anyOf", "additionalProperties"]
        for key in keywords:
            if key in childrenInfo.keys():
                childrenInfo = childrenInfo.get(key)
                if isinstance(childrenInfo, list):
                    childrenInfo = random.choice(childrenInfo)

                assert isinstance(childrenInfo, dict)
                if DocKey.REF_SIGN in childrenInfo.keys():
                    childrenInfo = AbstractParam.getRef(childrenInfo.get(DocKey.REF_SIGN), definitions)

        children = [buildParam(pInfo, definitions, pName) for pName, pInfo in
                    childrenInfo.get(DocKey.PROPERTIES).items()]
        info["children"] = children
        if isinstance(info.get("required"), list):
            for child in children:
                if child.name in info.get("required"):
                    child.required = True
        return cls(**info)

    def seeAllParameters(self) -> List[AbstractParam]:
        allParameters = []
        for child in self._children:
            allParameters.extend(child.seeAllParameters())
        return allParameters

    def genDomain(self, opStr, responseChains, okValues) -> list:
        paramList = list()
        for parameter in self.seeAllParameters():
            if parameter is not self:
                paramList.extend(parameter.genDomain(opStr, responseChains, okValues))
        return paramList

    def genRandom(self):
        pass

    def printableValue(self, response):
        value = dict()
        for child in self._children:
            childValue = child.printableValue(response)
            if childValue is not None:
                value[child.name] = child.printableValue(response)
        return None if len(value.keys()) == 0 else value

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]):
        object_param = dict()
        for child in self._children:
            object_param.update({child.name: child.getValueDto(value_dict)})
        self.value = object_param
        return self.value


class ArrayParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str, itemParam: AbstractParam, minItems=1, maxItems=3,
                 unique=False):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

        # todo: make maxItems and minItems work
        self._item: AbstractParam = itemParam
        self._item.parent = self
        self._item.required = self.required
        self._item.isConstrained = self.isConstrained

        self._maxItems = maxItems
        self._minItems = minItems
        self._unique: bool = unique

        self.value: List = list()

        assert self._minItems <= self._maxItems

    @classmethod
    def buildArray(cls, info, definitions):
        itemInfo: dict = info.pop(ParamKey.ITEMS, {})
        if len(itemInfo) == 0:
            raise UnsupportedError("{} can not be transferred to ArrayParam".format(info))
        elif ParamKey.TYPE in itemInfo.keys():
            itemParam = buildParam(itemInfo, definitions, "_item")
            # info["specifiedName"] = ""
            info["itemParam"] = itemParam
            return cls(**info)
        elif DocKey.REF_SIGN in itemInfo.keys():
            ref_info = itemInfo.get(DocKey.REF_SIGN)
            itemInfoCopied = dict()
            itemInfoCopied.update(itemInfo)
            itemInfoCopied.update(AbstractParam.getRef(ref_info, definitions))
            itemParam = buildParam(itemInfoCopied, definitions, "_item")
            # info["specifiedName"] = ""
            info["itemParam"] = itemParam
            return cls(**info)
        else:
            raise UnsupportedError("{} can not be transferred to ArrayParam".format(info))

    def seeAllParameters(self) -> List[AbstractParam]:
        allParameters = self._item.seeAllParameters()
        return allParameters

    def genDomain(self, opStr, responseChains, okValues) -> list:
        return self._item.genDomain(opStr, responseChains, okValues)

    def genRandom(self):
        pass

    def printableValue(self, response):
        value = self._item.printableValue(response)
        if value is None:
            return None
        else:
            return [value]

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        array_param = list()
        array_param.append(self._item.getValueDto(value_dict))
        self.value = array_param
        return self.value


class BoolParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

        self._enum = [True, False]

    def genDomain(self, opStr, responseChains, okValues) -> list:
        self.domain = [(ValueType.Enum, False), (ValueType.Enum, True)]
        if not self.required:
            self.domain.append((ValueType.NULL, None))
        return [self]

    def genRandom(self):
        pass

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value


class EnumParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str, enum: list):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

        # enum value
        self.enum: list = enum

    def genDomain(self, opStr, responseChains, okValues) -> list:
        self.domain = [(ValueType.Enum, v) for v in self.enum]
        if not self.required:
            self.domain.append((ValueType.NULL, None))

        return [self]

    def genRandom(self):
        pass

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value


class FileParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

    @classmethod
    def buildFile(cls, name, info):
        return cls(name, **info)

    def genRandom(self):
        return [random.choice([
            "",
            "random",
            "long random long random"
        ])]

    def printableValue(self, response):
        value = super(FileParam, self).printableValue(response)
        if len(self.value) == 0:
            return None
        else:
            valueType, _ = self.value
            if valueType is ValueType.Random:
                return {'file': ('random.txt', value)}
            else:
                return value

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value


class NumberParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str, maximum=100, minimum=0, exclusiveMinimum=False,
                 exclusiveMaxiMum=False, multipleOf=0):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

        self._maximum = maximum
        self._minimum = minimum
        self._exclusiveMinimum: bool = exclusiveMinimum
        self._exclusiveMaximum: bool = exclusiveMaxiMum
        self._multipleOf = multipleOf

        assert self._minimum <= self._maximum

    def genRandom(self):
        maxV = self._maximum if not self._exclusiveMaximum else self._maximum - 1
        minV = self._minimum if not self._exclusiveMinimum else self._minimum + 1

        if self.type in [DataType.Double, DataType.Float]:
            randomValues = [random.uniform(minV, maxV) for _ in range(AbstractParam.randomCount)]
        else:
            randomValues = [random.randint(minV, maxV) for _ in range(AbstractParam.randomCount)]

        if self._multipleOf != 0:
            randomValues = map(lambda n: n * self._multipleOf, randomValues)
        return randomValues

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value


class StringParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str, maxLength=20, minLength=1):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

        self._maxLength = maxLength
        self._minLength = minLength

        assert self._minLength <= self._maxLength

    def genRandom(self):
        randomValues = ["".join(random.sample((string.ascii_letters + string.digits), random.randint(0, 36))) for _ in
                        range(AbstractParam.randomCount)]
        if self.format is DataType.Binary:
            randomValues = [s.encode("utf-8") for s in randomValues]
        elif self.format is DataType.Byte:
            randomValues = [base64.b64encode(s.encode("utf-8")).decode("utf-8") for s in randomValues]
        return randomValues

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value


class Date(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

    def genRandom(self):
        curTime = datetime.utcnow()
        return Date.getMutate(curTime)

    @staticmethod
    def getMutate(timeDto=None):
        timeFormat = "%Y-%m-%d"
        timeDto = datetime.utcnow() if timeDto is None else timeDto
        randomValues = list()
        randomValues.append(timeDto.strftime(timeFormat))
        for i in range(AbstractParam.randomCount - 1):
            if i % 2 == 0:
                randomValues.append((timeDto + timedelta(days=-i - 1)).strftime(timeFormat))
            else:
                randomValues.append((timeDto + timedelta(days=i + 1)).strftime(timeFormat))
        return randomValues

    def printableValue(self, response):
        value = super(Date, self).printableValue(response)
        if len(self.value) == 0:
            return None
        else:
            valueType, _ = self.value
            if valueType is ValueType.Random:
                try:
                    value = Date.getMutate(datetime.strptime(value, '%Y-%m-%d'))[0]
                except ValueError:
                    value = Date.getMutate()[0]
            return value

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value


class UuidParam(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

    def genRandom(self) -> list:
        pass

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value


class DateTime(AbstractParam):
    def __init__(self, specifiedName: str, default: list, loc: Loc, required: bool, paramType: DataType,
                 paramFormat: DataType, description: str):
        super().__init__(specifiedName, default, loc, required, paramType, paramFormat, description)

    def genRandom(self):
        curTime = datetime.utcnow()
        return DateTime.getMutate(curTime)

    @staticmethod
    def getMutate(timeDto):
        randomValues = list()
        randomValues.append(timeDto.isoformat(timespec='seconds'))
        for i in range(AbstractParam.randomCount - 1):
            if i % 2 == 0:
                randomValues.append((timeDto + timedelta(days=-i - 1)).isoformat(timespec='seconds'))
            else:
                randomValues.append((timeDto + timedelta(days=i + 1)).isoformat(timespec='seconds'))
        return randomValues

    def printableValue(self, response):
        value = super(DateTime, self).printableValue(response)
        if len(self.value) == 0:
            return None
        else:
            # valueType, _ = self.value
            # if valueType is ValueType.Random:
            #     try:
            #         value = DateTime.getMutate(datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ'))
            #     except ValueError:
            #         value = DateTime.getMutate(datetime.utcnow())[0]
            return value

    def getValueDto(self, value_dict: Dict[str, Tuple[ValueType, object]]) -> Union:
        self.value = value_dict.get(self.getGlobalName(), [])
        return self.value
