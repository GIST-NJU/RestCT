import json
from pathlib import Path
from src.Dto.keywords import DocKey, ParamKey, DataType, Method
from src.Dto.operation import Operation
from src.Dto.parameter import buildParam, Example
from src.Dto.operation import Response
from src.Exception.exceptions import UnsupportedError

URL_PREFIX = ""
DEFINITIONS = dict()


def parse():
    """
    1. parse definition for examples, definitions dto
    2. parse paths for operations dto
        2.1 get parameters dto
        2.2 get responses dto
        2.3 get examples dto
    """
    from src.restct import Config
    swagger = Path(Config.swagger)
    with swagger.open("r") as fp:
        spec = json.load(fp)

    # get url prefix for all resources' url in paths
    global URL_PREFIX
    URL_PREFIX = _compile_url(spec)

    # get definitions
    global DEFINITIONS
    DEFINITIONS = spec.get(DocKey.DEFINITIONS, {})

    # parse paths
    paths = spec.get(DocKey.PATHS, {})
    if len(paths) > 0:
        _parse_paths(paths)

    # parse definitions
    _parse_definition_example()


def _compile_url(spec: dict):
    """
    get url prefix, e.g. http://localhost:30000/v4/api
    :param spec: swagger dict
    :return: url prefix
    """
    protocol = spec.get(DocKey.SCHEMES, ["http"])[0]
    baseurl = spec.get(DocKey.BASEPATH, "")
    host = spec.get(DocKey.HOST, "")

    return "{}://{}/{}".format(protocol, host.strip("/"), baseurl.strip("/"))


def _parse_paths(paths: dict):
    """
    parse swagger paths to get all operations
    :param paths: swagger.get("paths")
    :return: operation list
    """
    for url_str, url_info in paths.items():
        extraParamList = url_info.get(DocKey.PARAMS, list())
        for method_name, method_info in url_info.items():
            if method_name not in [m.value for m in Method]:
                continue
            operation = Operation(URL_PREFIX.rstrip("/") + "/" + url_str.lstrip("/"), method_name)
            # process parameters
            paramList = method_info.get(DocKey.PARAMS, [])
            paramList.extend(extraParamList)
            for param_info in paramList:
                operation.addParam(buildParam(param_info, DEFINITIONS))
                if DocKey.EXAMPLE in param_info.keys():
                    example = Example(param_info.get(ParamKey.NAME), param_info.get(DocKey.EXAMPLE))
                    example.operation = operation
                    Example.members.add(example)

            # process responses
            for status_code, response_info in method_info.get(DocKey.RESPONSES, {}).items():
                operation.addResponse(Response.buildResponse(status_code, response_info, DEFINITIONS, operation))


def _parse_definition_example():
    """get example in definitions"""
    for def_info in DEFINITIONS.values():
        wholeExamples = def_info.get(DocKey.EXAMPLE)
        if wholeExamples is not None:
            if isinstance(wholeExamples, list):
                for e in wholeExamples:
                    _parse_whole_example(e)
            elif isinstance(wholeExamples, dict):
                _parse_whole_example(wholeExamples)
            else:
                raise UnsupportedError("{} can not be transferred to example".format(wholeExamples))
        if DataType(def_info.get(ParamKey.TYPE, DataType.NULL.value)) is DataType.Object:
            for p_name, p_info in def_info.get(DocKey.PROPERTIES).items():
                singleExample = p_info.get(DocKey.EXAMPLE, None)
                if singleExample is not None:
                    example = Example(p_name, singleExample)
                    Example.members.add(example)


def _parse_whole_example(exampleInfo: dict):
    if exampleInfo is None or len(exampleInfo) == 0:
        return
    for p_name, p_example in exampleInfo.items():
        if isinstance(p_example, list):
            if len(p_example) == 0:
                continue
            if isinstance(p_example[0], list):
                raise UnsupportedError("{} can not be transferred to example".format(p_example))
            elif isinstance(p_example[0], dict):
                for sub_example in p_example:
                    _parse_whole_example(sub_example)
            else:
                example = Example(p_name, p_example)
                Example.members.add(example)
        elif isinstance(p_example, dict):
            _parse_whole_example(p_example)
        else:
            example = Example(p_name, p_example)
            Example.members.add(example)
