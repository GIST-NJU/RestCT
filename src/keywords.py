from enum import Enum


class DocKey:
    # 文档
    REF_SIGN = "$ref"
    ALL_OF = "allOf"
    ONE_OF = "oneOf"
    ANY_OF = "anyOf"
    ADDITIONAL_PROPERTIES = "additionalProperties"

    SCHEMES = "schemes"
    BASEPATH = "basePath"
    DEFINITIONS = "definitions"
    PATHS = "paths"
    HOST = "host"
    PROTOCOL = "protocol"
    PARAMS = "parameters"
    RESPONSES = "responses"
    PROPERTIES = "properties"
    EXAMPLE = "example"


class ParamKey:
    # 参数
    NAME = "name"
    TYPE = "type"
    FORMAT = "format"
    ENUM = "enum"
    DEFAULT = "default"
    DESCRIPTION = "description"
    REQUIRED = "required"
    MAXITEMS = "maxItems"
    MINITEMS = "minItems"
    UNIQUEITEMS = "uniqueItems"
    MAXIMUM = "maximum"
    MINIMUM = "minimum"
    EXCLUSIVEMAXIMUM = "exclusiveMaximum"
    EXCLUSIVEMINIMUM = "exclusiveMinimum"
    MULTIPLEOF = "multipleOf"
    MAXLENGTH = "maxLength"
    MINLENGTH = "minLength"

    ITEMS = "items"
    LOCATION = "in"

    SCHEMA = "schema"


class DataType(Enum):
    # 数字
    Integer = "integer"
    Number = "number"
    Int32 = "int32"
    Int64 = "int64"
    Float = "float"
    Double = "double"
    Long = "long"
    # 字符串
    String = "string"
    Byte = "byte"
    Binary = "binary"
    Date = "date"
    DateTime = "datetime"
    Password = "password"
    # 布尔
    Bool = "boolean"
    # 文件
    File = "file"
    UUID = "uuid"
    # 复杂类型
    Array = "array"
    Object = "object"

    NULL = "NONE"

    @staticmethod
    def from_string(value, value_type):
        try:
            if value_type in [DataType.Integer, DataType.Int32, DataType.Int64, DataType.Long]:
                value = int(value)
            elif value_type in [DataType.Float, DataType.Double, DataType.Number]:
                value = float(value)
            elif value_type in [DataType.String]:
                value = str(value)
            elif value_type in [DataType.Byte]:
                value = bytes(value)
            elif value_type in [DataType.Bool]:
                if str(value).lower() == "true":
                    value = True
                else:
                    value = False
        except (ValueError, TypeError):
            return value
        return value


class Loc(Enum):
    FormData = "formData"
    Body = "body"
    Query = "query"
    Path = "path"
    Header = "header"

    NULL = "NONE"


class Method(Enum):
    POST = "post"
    GET = "get"
    DELETE = "delete"
    PUT = "put"
    OPTIONS = "options"
    HEAD = "head"
    PATCH = "patch"

    @classmethod
    def of(cls, text: str):
        text_lower = text.lower()
        for member in cls.__members__.values():
            if member.value.lower() == text_lower:
                return member
        else:
            raise ValueError(f"Unknown method: {text}")


class URL:
    baseurl = ""
