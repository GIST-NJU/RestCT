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


class RestPath:
    class Element:
        def __init__(self, tokens: list):
            self.tokens = tokens

        def __repr__(self):
            return "".join([t.__repr__() for t in self.tokens])

        def __str__(self):
            return self.__repr__()

        def __eq__(self, other):
            if not isinstance(other, RestPath.Element):
                return False

            return all([t == other.tokens[i] for i, t in enumerate(self.tokens)])

    class Token:
        def __init__(self, name: str, is_parameter: bool):
            self._name = name
            self._is_parameter = is_parameter

        def __repr__(self):
            return "{" + self._name + "}" if self._is_parameter else self._name

        def __str__(self):
            return self.__repr__()

        def __eq__(self, other):
            if not isinstance(other, RestPath.Token):
                return False

            return self._name == other._name and self._is_parameter == self._is_parameter

    @staticmethod
    def _extract_element(s):
        tokens = []
        _next = 0
        while _next < len(s):
            current = _next
            if s[_next] == '{':
                closing = s.find("}", current)
                if closing < 0:
                    raise ValueError("Opening { but missing closing } in: " + s)
                _next = closing + 1

                tokens.append(RestPath.Token(s[current + 1:_next - 1], True))
            else:
                _next = s.find("{", current)
                _next = len(s) if _next < 0 else _next
                tokens.append(RestPath.Token(s[current:_next], False))
        return RestPath.Element(tokens)

    def __init__(self, path):
        if "?" in path or "#" in path:
            raise ValueError("The path contains invalid characters. "
                             "Are you sure you didn't pass a full URI?\n" + path)

        self.elements = [self._extract_element(element) for element in path.split("/") if element != ""]

        self.computed_to_string = "/" + "/".join(
            ["".join([str(t).replace("[\\[\\],]", "") for t in e.tokens]) for e in self.elements])

    def is_ancestor_of(self, other):
        if len(self.elements) > len(other.elements):
            return False

        for i, e in enumerate(self.elements):
            if e.__repr__() != other.elements[i].__repr__():
                return False

        return True

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, RestPath): return False

        return all([e == o.elements[i] for i, e in enumerate(self.elements)])


class Operation:
    def __init__(self, url: str, method):
        self.path = RestPath(url)
        self.method: Method = Method(method)

        self.parameterList: List[AbstractParam] = list()
        self.responseList: List[Response] = list()

        self.constraints = list()

    # def genDomain(self, responseChain, okValues):
    #     paramList = list()
    #     for param in self.parameterList:
    #         paramList.extend(param.genDomain(self.__repr__(), responseChain, okValues))
    #     return paramList

    @property
    def url(self):
        return self.path.computed_to_string

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

    def set_constraints(self, constraints: List[Constraint]):
        self.constraints = constraints

    def __hash__(self):
        return hash(self.url + self.method.value)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.url == other.url and self.method == other.method:
            return True
        else:
            return False

    def __repr__(self) -> str:
        return self.method.value + "***" + self.url
