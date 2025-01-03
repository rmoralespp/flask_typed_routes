import collections
import dataclasses
import typing as t

import pydantic

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.utils as ftr_utils

# Request parameter types
PARAMETER_TYPES = (
    ftr_fields.FieldTypes.path,
    ftr_fields.FieldTypes.query,
    ftr_fields.FieldTypes.cookie,
    ftr_fields.FieldTypes.header,
)
PARAMETER_TYPES = frozenset(PARAMETER_TYPES)

# Component schemas prefix
REF_PREFIX = "#/components/schemas/"

# Validation errors response
VALIDATION_ERROR_KEY = "ValidationError"
VALIDATION_ERROR_DEF = {
    "title": VALIDATION_ERROR_KEY,
    "type": "object",
    "properties": {
        "loc": {
            "title": "Location",
            "type": "array",
            "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        },
        "msg": {"title": "Message", "type": "string"},
        "type": {"title": "Error Type", "type": "string"},
    },
    "required": ["loc", "msg", "type"],
}
HTTP_VALIDATION_ERROR_KEY = "HTTPValidationError"
HTTP_VALIDATION_ERROR_DEF = {
    "title": HTTP_VALIDATION_ERROR_KEY,
    "type": "object",
    "properties": {
        "errors": {
            "title": "Errors",
            "type": "array",
            "items": {"$ref": REF_PREFIX + VALIDATION_ERROR_KEY},
        }
    },
}
HTTP_VALIDATION_ERROR_REF = {
    "description": "Validation Error",
    "content": {"application/json": {"schema": {"$ref": REF_PREFIX + HTTP_VALIDATION_ERROR_KEY}}},
}


class Operation(pydantic.BaseModel):
    """
    Describes an API operations on a path.
    It is used to generate OpenAPI specification for the route.
    """

    tags: t.Optional[list[str]] = None
    summary: t.Optional[str] = None
    description: t.Optional[str] = None
    externalDocs: t.Optional[dict] = None
    operationId: t.Optional[str] = None
    parameters: t.Optional[list[dict]] = None
    requestBody: t.Optional[dict] = None
    responses: t.Optional[dict[str, dict]] = None
    callbacks: t.Optional[dict[str, dict]] = None
    deprecated: t.Optional[bool] = None
    security: t.Optional[list[dict[str, list[str]]]] = None
    servers: t.Optional[list[dict]] = None


@dataclasses.dataclass(frozen=True)
class OpenAPI:
    """
    OpenAPI specification for typed routes.

    :param dict paths: The available paths and operations for the API.
    :param dict components_schemas: Reusable schema objects that are inferred from Pydantic models.
    """

    paths: dict
    components_schemas: dict[str:dict]


def duplicate_request_field(field):
    msg = f"Duplicate request parameter: [name={field.locator}, in={field.kind}]"
    return ftr_errors.InvalidParameterTypeError(msg)


def duplicate_request_body():
    return ftr_errors.InvalidParameterTypeError("Duplicate request body")


def get_parameters(fields, model_properties, model_components, model_required_fields):
    """
    Get OpenAPI operation parameters.

    :param Iterable[flask_typed_routes.Field] fields: Field definitions
    :param model_properties:
    :param model_components:
    :param model_required_fields:

    :rtype: Iterable[dict]
    """

    params = collections.defaultdict(dict)
    params_fields = (field for field in fields if field.kind in PARAMETER_TYPES)
    for field in params_fields:
        slot = params[field.kind]
        if ftr_utils.is_subclass(field.annotation, pydantic.BaseModel):
            ref_properties = model_properties[field.locator]
            ref_name = ref_properties["$ref"].split("/")[-1]
            ref_schema = model_components[ref_name]
            properties_slot = ref_schema.get("properties", dict())
            required_slot = ref_schema.get("required", ())
            names = (info.alias or name for name, info in field.annotation.model_fields.items())
        else:
            properties_slot = model_properties
            required_slot = model_required_fields
            names = (field.locator,)

        for name in names:
            if name in slot:
                raise duplicate_request_field(field)
            else:
                schema = properties_slot[name]
                _ = schema.pop("title", None)  # title is dont used
                description = schema.pop("description", None)
                examples = schema.pop("examples", ())
                examples = {f"{name}-{i}": {"value": value} for i, value in enumerate(examples, 1)}
                deprecated = schema.pop("deprecated", False)
                param_spec = {
                    "name": name,
                    "in": field.kind,
                    "required": name in required_slot,
                    "schema": schema,
                }
                if description:
                    param_spec["description"] = description
                if deprecated:
                    param_spec["deprecated"] = deprecated
                if examples:
                    param_spec["examples"] = examples
                slot[name] = param_spec

    for value in params.values():
        yield from value.values()


def get_request_body(fields, model_properties, model_required_fields):
    """
    Get OpenAPI operation Request body.

    :param model_properties:
    :param model_required_fields:

    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
    :rtype: Iterable[dict]
    """

    required_fields = []
    required = False
    body_fields = (field for field in fields if field.kind == ftr_fields.FieldTypes.body)

    schema_ref = dict()
    schema_obj = dict()

    for field in body_fields:
        name = field.locator
        if schema_ref:
            raise duplicate_request_body()

        elif issubclass(field.annotation, pydantic.BaseModel):
            if field.embed:
                if name in schema_obj:
                    raise duplicate_request_field(field)
                else:
                    schema_obj[name] = model_properties[field.locator]
                    if name in model_required_fields:
                        required_fields.append(name)

            elif schema_obj:
                raise duplicate_request_body()
            else:
                schema_ref = model_properties[field.locator]
                required = field.is_required

        elif name in schema_obj:
            raise duplicate_request_field(field)
        else:
            schema_obj[name] = model_properties[field.locator]
            if name in model_required_fields:
                required_fields.append(name)

    if schema_obj:
        config = {
            "schema": {
                "type": "object",
                "properties": schema_obj,
                "required": required_fields,
            },
        }
        return {
            "required": bool(required_fields),
            "content": {"application/json": config},
        }
    elif schema_ref:
        examples = schema_ref.pop("examples", ())
        examples = {f"example-{i}": {"value": value} for i, value in enumerate(examples, 1)}
        config = {"schema": schema_ref}
        if examples:
            config["examples"] = examples
        return {
            "required": required,
            "content": {"application/json": config},
        }
    else:
        return None


def get_route_spec(func, rule, endpoint, methods):
    """
    Describes an API operations on a path.

    :param func: Flask view function
    :param str rule: URL rule
    :param str endpoint: Endpoint name
    :param Iterable[str] methods: HTTP methods

    :return dict: OpenAPI specification for the route
    """

    request_model = getattr(func, ftr_utils.TYPED_ROUTE_REQUEST_MODEL, None)
    request_fields = getattr(func, ftr_utils.TYPED_ROUTE_PARAM_FIELDS, None)
    status_code = getattr(func, ftr_utils.TYPED_ROUTE_STATUS_CODE, None)
    override_spec = getattr(func, ftr_utils.TYPED_ROUTE_OPENAPI, None)

    paths = collections.defaultdict(dict)
    schemas = dict()
    if request_model and request_fields:
        rule_path = ftr_utils.format_openapi_path(rule)
        ref_template = "{prefix}{endpoint}.{{model}}".format(prefix=REF_PREFIX, endpoint=endpoint)
        model_schema = request_model.model_json_schema(ref_template=ref_template)
        model_properties = model_schema.get("properties", dict())
        model_components = model_schema.get("$defs", dict())
        schemas = {f"{endpoint}.{name}": schema for name, schema in model_components.items()}
        model_required_fields = frozenset(model_schema.get("required", ()))

        parameters = get_parameters(request_fields, model_properties, schemas, model_required_fields)
        request_body = get_request_body(request_fields, model_properties, model_required_fields)
        responses = {"400": HTTP_VALIDATION_ERROR_REF}
        spec = {
            "parameters": tuple(parameters),
            "description": ftr_utils.cleandoc(func),
            "operationId": endpoint,
            "summary": ftr_utils.get_summary(func),
            "responses": responses,
        }
        if status_code:
            responses[str(status_code)] = {"description": "Successful operation"}
        if request_body:
            spec["requestBody"] = request_body
        if override_spec:
            override_spec = override_spec.model_dump(exclude_unset=True, exclude_defaults=True, exclude_none=True)
            spec.update(override_spec)
        for method in methods:
            paths[rule_path][method.lower()] = spec

    return {
        "paths": paths,
        "components": {"schemas": schemas},
    }
