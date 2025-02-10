from urllib.parse import urlparse, urlunparse

import prance
from loguru import logger
from openapi_parser.parser import _create_parser
from openapi_parser.specification import *

from src.config import Config
from src.factor import *
from src.rest import *


def recursion_limit_handler(limit, parsed_url, recursions=()):
    """https://github.com/RonnyPfannschmidt/prance/blob/main/COMPATIBILITY.rst"""
    return None


class SwaggerParser:
    def __init__(self, config: Config):
        swagger_path = config.swagger
        server = config.server if config.server is not None else None

        _resolver = prance.ResolvingParser(url=swagger_path,
                                           strict=False,
                                           lazy=True,
                                           recursion_limit_handler=recursion_limit_handler)
        try:
            logger.debug(f"Parsing specification file")
            _resolver.parse()
            specification = _resolver.specification
        except prance.ValidationError as error:
            raise ValueError(f"OpenAPI validation error: {error}")
        except Exception as error:
            raise ValueError(f"OpenAPI file parsing error: {error}")

        _parser = _create_parser(strict_enum=True)

        # 解析swagger文件
        self._swagger: Specification = _parser.load_specification(specification)

        # 可能有多个server，只存一个
        self._server: str = self._get_server(server)

    def _get_server(self, specified):
        """
        get bash path of url
        """
        server = self._swagger.servers[0]
        parsed = urlparse(server.url)
        if parsed.scheme == 0 or parsed.netloc == 0:
            raise ValueError(f"Invalid URI {server.url}: Scheme and netloc are required.")
        if specified is not None:
            specified = urlparse(specified)
            return urlunparse(
                (specified.scheme, specified.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        return parsed.geturl()

    def extract(self):
        operations = []
        for path in self._swagger.paths:
            path_parameters = path.parameters

            for operation in path.operations:
                rest_op = RestOp(self._server, path.url, operation.method.name)

                if operation.description is not None and len(operation.description):
                    rest_op.description = operation.description

                # handle with input parameters
                for param in operation.parameters:
                    rest_param = self._extract_param(param)
                    rest_op.parameters.append(rest_param)

                if len(path_parameters) > 0:
                    for param in path_parameters:
                        rest_param = self._extract_param(param)
                        rest_op.parameters.append(rest_param)

                # handle request body
                if operation.request_body is not None:
                    if not len(operation.request_body.content) == 0:
                        rest_op.parameters.append(self._extract_body_param(operation.request_body))

                for r in operation.responses:
                    if r.code is None:
                        continue
                    response = RestResponse(r.code, r.description)
                    if r.content is not None:
                        for c in r.content:
                            content_type = c.type
                            content = SwaggerParser._extract_factor("response", c.schema)
                            response.add_content(content, content_type.name)
                    rest_op.responses.append(response)
                operations.append(rest_op)
        return operations

    @staticmethod
    def _extract_body_param(body: RequestBody):
        content = body.content
        if len(content) == 0:
            raise ValueError("no content is provided")

        content = content[0]

        factor: AbstractFactor = SwaggerParser._extract_factor("body", content.schema)
        if body.description is not None and len(body.description) != 0:
            factor.set_description(body.description)

        return BodyParam(factor, content.type.value)

    @staticmethod
    def _extract_param(param: Parameter):
        """
        extract factor from swagger
        """
        # factor info: AbstractFactor
        factor: AbstractFactor = SwaggerParser._extract_factor(param.name, param.schema)
        factor.required = param.required
        factor.set_description(param.description if param.description is not None else None)
        if param.location is ParameterLocation.QUERY:
            rest_param = QueryParam(factor)
        elif param.location is ParameterLocation.HEADER:
            rest_param = HeaderParam(factor)
        elif param.location is ParameterLocation.PATH:
            rest_param = PathParam(factor)
        else:
            raise ValueError(f"Unsupported factor location: {param.location}")
        return rest_param

    @staticmethod
    def _extract_factor(name: str, schema: Schema):
        if isinstance(schema, Null):
            raise ValueError(f"Parameter {name} has no schema")
        if len(schema.enum) > 0:
            factor = EnumFactor(name, schema.enum)
        elif isinstance(schema, Boolean):
            factor = BooleanFactor(name)
        elif isinstance(schema, Integer):
            factor = SwaggerParser._build_integer_factor(name, schema)
        elif isinstance(schema, Number):
            factor = SwaggerParser._build_number_factor(name, schema)
        elif isinstance(schema, String):
            factor = SwaggerParser._build_string_factor(name, schema)
        elif isinstance(schema, Array):
            factor = SwaggerParser._build_array_factor(name, schema)
        elif isinstance(schema, Object):
            factor = SwaggerParser._build_object_factor(name, schema)
        elif isinstance(schema, (AnyOf, OneOf)):
            _schema = next(filter(lambda x: x.type is DataType.Object, schema.schemas), None)
            if _schema is None:
                _schema = next(filter(lambda x: x.type is DataType.Array, schema.schemas), None)
            if _schema is None:
                _schema = schema.schemas[0]
            factor = SwaggerParser._extract_factor(name, _schema)
        else:
            raise ValueError(f"{name} -> Unsupported schema: {schema}")

        if not isinstance(factor, (ObjectFactor, ArrayFactor)):
            if schema.example is not None:
                factor.set_example(schema.example)
            if schema.default is not None:
                factor.set_default(schema.default)
        if schema.description is not None:
            factor.set_description(schema.description)

        return factor

    @staticmethod
    def _build_object_factor(name: str, schema: Object):
        object_factor = ObjectFactor(name)

        if len(schema.required) == 0:
            schema.required = [_.name for _ in schema.properties]

        for p in schema.properties:
            p_factor = SwaggerParser._extract_factor(p.name, p.schema)
            if p_factor.name not in schema.required:
                p_factor.required = False
            object_factor.add_property(p_factor)

        return object_factor

    @staticmethod
    def _build_array_factor(name: str, schema: Array):
        min_items = schema.min_items if schema.min_items is not None else 1
        array = ArrayFactor(name)
        if schema.items is None:
            raise ValueError(f"Parameter {name} has no items")
        item_factor = SwaggerParser._extract_factor("_item", schema.items)
        array.set_item(item_factor)
        return array

    @staticmethod
    def _build_string_factor(name: str, schema: String):
        if schema.pattern is not None:
            pass
        return StringFactor(name,
                            format=schema.format.value if schema.format is not None else None,
                            min_length=schema.min_length if schema.min_length is not None else 1,
                            max_length=schema.max_length if schema.max_length is not None else 100)

    @staticmethod
    def _build_integer_factor(name: str, schema: Integer):
        return IntegerFactor(
            name=name,
            minimum=schema.minimum if schema.minimum is not None else -1000,
            maximum=schema.maximum if schema.maximum is not None else 1000,
        )

    @staticmethod
    def _build_number_factor(name: str, schema: Number):
        return NumberFactor(
            name=name,
            minimum=schema.minimum if schema.minimum is not None else -1000,
            maximum=schema.maximum if schema.maximum is not None else 1000,
        )


if __name__ == '__main__':
    import json

    root_path = "/Users/naariah/Documents/Python_Codes/api-suts/specifications/v3"
    config = Config()
    leave_dict = {}
    for f in os.listdir(root_path):
        if "gitlab" in f:
            sut_name = f.split("-")[1]
            config.swagger = f"{root_path}/{f}"
            leave_dict[sut_name] = {}
            parser = SwaggerParser(config)
            operations = parser.extract()
            for op in operations:
                leaves = []
                for p in op.parameters:
                    leave = p.factor.get_leaves()
                    for l in leave:
                        leaves.append(l.__repr__())
                leave_dict[sut_name][op.id] = leaves

    with open("/Users/naariah/Documents/Python_Codes/api-exp-scripts/leave_dict.json", "w") as f:
        json.dump(leave_dict, f, indent=4)
