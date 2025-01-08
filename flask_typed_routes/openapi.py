import collections

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
HTTP_SUCCESS_RESPONSE = {
    "description": "Success",
    "content": {"application/json": {"schema": {"type": "string"}}},
}


def duplicate_request_field(field, /):
    msg = f"Duplicate request parameter: [name={field.locator}, in={field.kind}]"
    return ftr_errors.InvalidParameterTypeError(msg)


def duplicate_request_body():
    return ftr_errors.InvalidParameterTypeError("Duplicate request body")


def get_summary(func, /):
    """Get the summary for the OpenAPI operation."""

    return " ".join(word.capitalize() for word in func.__name__.split("_") if word)


def get_parameters(fields, model_properties, model_components, model_required_fields, /):
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
            required_slot = frozenset(ref_schema.get("required", ()))
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


def get_request_body(fields, model_properties, model_required_fields, /):
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
            if field.embed and name in schema_obj:
                raise duplicate_request_field(field)
            elif field.embed:
                schema_obj[name] = model_properties[name]
                if name in model_required_fields:
                    required_fields.append(name)
            elif schema_obj:
                raise duplicate_request_body()
            else:
                schema_ref = model_properties[name]
                required = field.is_required
        elif name in schema_obj:
            raise duplicate_request_field(field)
        else:
            schema_obj[name] = model_properties[name]
            if name in model_required_fields:
                required_fields.append(name)

    if schema_obj:
        return {
            "required": bool(required_fields),
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": schema_obj,
                        "required": required_fields,
                    },
                }
            },
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


def get_operations(func, rule, endpoint, methods, /):
    """
    Get OpenAPI operations for a flask view function.

    :param func: Flask view function
    :param str rule: URL rule
    :param str endpoint: Endpoint name
    :param Iterable[str] methods: HTTP methods
    :rtype dict:
    """

    request_model = getattr(func, ftr_utils.TYPED_ROUTE_REQUEST_MODEL, None)
    param_fields = getattr(func, ftr_utils.TYPED_ROUTE_PARAM_FIELDS, None)
    status_code = getattr(func, ftr_utils.TYPED_ROUTE_STATUS_CODE, None)
    override_spec = getattr(func, ftr_utils.TYPED_ROUTE_OPENAPI, None)

    paths = collections.defaultdict(dict)
    schemas = dict()
    if request_model and param_fields:
        path = ftr_utils.format_openapi_path(rule)
        ref_template = f"{REF_PREFIX}{endpoint}.{{model}}"
        model_schema = request_model.model_json_schema(ref_template=ref_template)
        required_fields = frozenset(model_schema.get("required", ()))
        properties = model_schema.get("properties", dict())
        components = model_schema.get("$defs", dict())
        # Include endpoint in the schema name to avoid conflicts with other models with the same name
        schemas = {f"{endpoint}.{name}": schema for name, schema in components.items()}

        parameters = get_parameters(param_fields, properties, schemas, required_fields)
        request_body = get_request_body(param_fields, properties, required_fields)
        status_code = f"{status_code}" if status_code else "default"
        responses = {
            "400": HTTP_VALIDATION_ERROR_REF,
            status_code: HTTP_SUCCESS_RESPONSE,
        }

        spec = {
            "parameters": tuple(parameters),
            "description": ftr_utils.cleandoc(func),
            "operationId": endpoint,
            "summary": get_summary(func),
            "responses": responses,
        }

        if request_body:
            spec["requestBody"] = request_body
        if override_spec:
            spec.update(override_spec)
        for method in methods:
            paths[path][method.lower()] = spec

    return {
        "paths": paths,
        "components": {"schemas": schemas},
    }


def get_operation(
    *,
    tags: list[str] = None,
    summary: str = None,
    description: str = None,
    externalDocs: dict = None,
    operationId: str = None,
    parameters: list[dict] = None,
    requestBody: dict = None,
    responses: dict[str, dict] = None,
    callbacks: dict[str, dict] = None,
    deprecated: bool = None,
    security: list[dict[str, list[str]]] = None,
    servers: list[dict] = None,
):
    """Get specification of OpenAPI operation according to the given parameters."""

    result = dict()
    if tags:
        result["tags"] = tags
    if summary:
        result["summary"] = summary
    if description:
        result["description"] = description
    if externalDocs:
        result["externalDocs"] = externalDocs
    if operationId:
        result["operationId"] = operationId
    if parameters:
        result["parameters"] = parameters
    if requestBody:
        result["requestBody"] = requestBody
    if responses:
        result["responses"] = responses
    if callbacks:
        result["callbacks"] = callbacks
    if deprecated:
        result["deprecated"] = deprecated
    if security:
        result["security"] = security
    if servers:
        result["servers"] = servers
    return result


def get_openapi(
    *,
    title: str = "API doc",
    version: str = "0.0.0",
    openapi_version: str = "3.1.0",
    summary: str = None,
    description: str = None,
    terms_of_service: str = None,
    contact_info: dict = None,
    license_info: dict = None,
    servers: list[dict] = None,
    webhooks: dict[str, dict] = None,
    components: dict = None,
    security=None,
    tags: list[dict] = None,
    external_docs: dict = None,
):
    """Get specification of OpenAPI document according to the given parameters."""

    info = {"title": title, "version": version}
    if summary:
        info["summary"] = summary
    if description:
        info["description"] = description
    if terms_of_service:
        info["termsOfService"] = terms_of_service
    if contact_info:
        info["contact"] = contact_info
    if license_info:
        info["license"] = license_info

    result = {
        "openapi": openapi_version,
        "info": info,
        "paths": collections.defaultdict(dict),
        "components": {
            "schemas": {
                VALIDATION_ERROR_KEY: VALIDATION_ERROR_DEF,
                HTTP_VALIDATION_ERROR_KEY: HTTP_VALIDATION_ERROR_DEF,
            },
        },
    }
    if servers:
        result["servers"] = servers
    if webhooks:
        result["webhooks"] = webhooks
    if components:
        result["components"].update(components)
    if security:
        result["security"] = security
    if tags:
        result["tags"] = tags
    if external_docs:
        result["externalDocs"] = external_docs
    return result
