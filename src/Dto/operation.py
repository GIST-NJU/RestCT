from src.Dto.keywords import Method, ParamKey, DocKey
from src.Dto.parameter import AbstractParam, buildParam
from src.Dto.constraint import Constraint
from src.Exception.exceptions import UnsupportedError
from typing import List, Set, Tuple


class Response:
    def __init__(self, status_code, template, operation):
        self.expected_status_code = status_code
        self.template: AbstractParam = template
        self.operation = operation

    @classmethod
    def buildResponse(cls, statusCode, info, definitions, operation):
        schema = info.get(ParamKey.SCHEMA, None)
        if schema is None:
            # status_code: 204, response_info: {'description': 'Deletes a project'}
            content = None
        else:
            ref_info = schema.get(DocKey.REF_SIGN, None)
            s_type = schema.get(ParamKey.TYPE, None)
            if ref_info is not None:
                ref = AbstractParam.getRef(ref_info, definitions)
                content = buildParam(ref, definitions)
            elif s_type is not None:
                content = buildParam(schema, definitions)
            else:
                raise UnsupportedError("{} can not be transferred to Response".format(info))
        return cls(statusCode, content, operation)


class Operation:
    members = list()

    def __init__(self, url: str, method):
        self.url = url
        self.method: Method = Method(method)

        self.parameterList: List[AbstractParam] = list()
        self.responseList: List[Response] = list()

        self.constraints = list()

        Operation.members.append(self)

    def genDomain(self, responseChain, okValues):
        paramList = list()
        for param in self.parameterList:
            paramList.extend(param.genDomain(self.__repr__(), responseChain, okValues))
        return paramList

    def addParam(self, param: AbstractParam):
        self.parameterList.append(param)

    def addResponse(self, response: Response):
        self.responseList.append(response)

    def _flatMapParameter(self):
        allParameters = list()
        for param in self.parameterList:
            allParameters.extend(param.seeAllParameters())
        return allParameters

    @property
    def splittedUrl(self) -> Set[Tuple[str, int]]:
        return {(part, index) for index, part in enumerate(self.url.split("/"))}

    def addConstraints(self, constraints: List[Constraint]):
        self.constraints.extend(constraints)

    def __hash__(self):
        return hash(self.url + self.method.value)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.url == other.url and self.method == other.method:
            return True
        else:
            return False

    def __repr__(self) -> str:
        return self.method.value + "***" + self.url
