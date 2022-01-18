from src.Dto.parameter import buildParam
from src.Dto.parameter import AbstractParam
from src.Dto.keywords import ParamKey, DocKey
from src.Exception.exceptions import UnsupportedError


class Response:
    def __init__(self, status_code, content):
        self.expected_status_code = status_code
        self.content: AbstractParam = content

    @classmethod
    def buildResponse(cls, statusCode, info, definitions):
        schema = info.get(ParamKey.SCHEMA, None)
        if schema is None:
            # status_code: 204, response_info: {'description': 'Deletes a project'}
            content = None
        else:
            ref_info = schema.get(DocKey.REF_SIGN, None)
            s_type = schema.get(ParamKey.TYPE, None)
            if ref_info is not None:
                ref = AbstractParam.get_ref(ref_info, definitions)
                content = buildParam(ref, definitions)
            elif s_type is not None:
                content = buildParam(schema, definitions)
            else:
                raise UnsupportedError("{} can not be transferred to Response".format(info))
        return cls(statusCode, content)
