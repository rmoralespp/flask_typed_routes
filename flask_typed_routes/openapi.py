import collections
import itertools

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


def get_summary(operation_id, /):
    """Get the summary for the OpenAPI operation."""

    return " ".join(word.capitalize() for word in operation_id.split("_") if word)


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


def get_unvalidated_parameters(path_args):
    """
    Get OpenAPI operation parameters for unvalidated fields.

    :param Iterable[str] path_args: Parameters of the route rule
    :rtype: Iterable[dict]
    """

    for name in path_args:
        yield {
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        }


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


def get_operations(func, rule, func_name, methods, path_args, validation_error_status_code, /):
    """
    Get OpenAPI operations for a flask view function.

    :param func: Flask view function
    :param str rule: URL rule
    :param str func_name: Safe function name
    :param Iterable[str] methods: HTTP methods
    :param path_args: Parameters of the route rule
    :param int validation_error_status_code: Status code for validation errors response.
    :rtype dict:
    """

    request_model_schema = getattr(func, ftr_utils.TYPED_ROUTE_REQUEST_MODEl_SCHEMA, None)
    param_fields = getattr(func, ftr_utils.TYPED_ROUTE_PARAM_FIELDS, None)
    status_code = getattr(func, ftr_utils.TYPED_ROUTE_STATUS_CODE, None)
    override_spec = getattr(func, ftr_utils.TYPED_ROUTE_OPENAPI, None)

    paths = collections.defaultdict(dict)
    schemas = dict()
    path = ftr_utils.format_openapi_path(rule)
    status_code = status_code or "default"

    if request_model_schema and param_fields:
        required_fields = frozenset(request_model_schema.get("required", ()))
        properties = request_model_schema.get("properties", dict())

        parameters = get_parameters(param_fields, properties, schemas, required_fields)
        request_body = get_request_body(param_fields, properties, required_fields)
        spec = {
            "parameters": tuple(parameters),
            "description": ftr_utils.cleandoc(func),
            "responses": {
                str(validation_error_status_code): HTTP_VALIDATION_ERROR_REF,
                str(status_code): HTTP_SUCCESS_RESPONSE,
            },
        }
        if request_body:
            spec["requestBody"] = request_body
    else:
        spec = {
            "parameters": tuple(get_unvalidated_parameters(path_args)),
            "description": ftr_utils.cleandoc(func),
            "responses": {status_code: HTTP_SUCCESS_RESPONSE},
        }

    if override_spec:
        spec.update(override_spec)

    operation_id = spec.get("operationId")
    summary = spec.get("summary")
    for method in methods:
        method = method.lower()
        # Include the method in the operation ID to avoid conflicts with other operations
        method_id = operation_id or f"{func_name}_{method}"
        method_summary = summary or get_summary(method_id)
        operation = {**spec, "operationId": method_id, "summary": method_summary}
        paths[path][method] = operation

    return paths


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


class OpenApi:

    def __init__(
        self,
        validation_error_status_code,
        *,
        title: str = "API doc",
        version: str = "0.0.0",
        openapi_version: str = "3.1.0",
        openapi_url_prefix: str = "/openapi",
        openapi_url_json: str = "swagger.json",
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

        self.schema = {
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
            self.schema["servers"] = servers
        if webhooks:
            self.schema["webhooks"] = webhooks
        if components:
            self.schema["components"].update(components)
        if security:
            self.schema["security"] = security
        if tags:
            self.schema["tags"] = tags
        if external_docs:
            self.schema["externalDocs"] = external_docs

        self.schema_generator = pydantic.json_schema.GenerateJsonSchema(by_alias=True, ref_template=REF_PREFIX + "{model}")
        self.openapi_url_prefix = openapi_url_prefix
        self.openapi_url_json = openapi_url_json
        self.models = []
        self.validation_error_status_code = validation_error_status_code

    def register_route(self, func, rule, func_name, methods, /):
        path_args = ftr_utils.extract_rule_params(rule)
        paths = get_operations(func, rule, func_name, methods, path_args, self.validation_error_status_code)
        self.register_openapi_paths(paths)

    def register_openapi_paths(self, paths, /):
        current = self.schema["paths"]
        for path, spec in paths.items():
            current[path].update(spec)

    def openapi_json_view(self, routes):
        models = dict()
        for route in routes:
            if not route.rule_url.startswith(self.openapi_url_prefix):
                view_func = route.view_func
                view_model = getattr(view_func, ftr_utils.TYPED_ROUTE_REQUEST_MODEL, None)
                if view_model:
                    models[view_model] = route

        if models:
            validation_models = zip(models, itertools.repeat("validation"))
            validation_models = tuple(validation_models)
            schemas_map, schemas = pydantic.json_schema.models_json_schema(
                validation_models,
                ref_template=REF_PREFIX + "{model}"
            )
            definitions = schemas["$defs"]

            for model, mode in schemas_map:
                model_schema_ref = schemas_map[(model, mode)]["$ref"].split("/")[-1]
                model_schema = definitions.pop(model_schema_ref)
                route = models[model]
                setattr(route.view_func, ftr_utils.TYPED_ROUTE_REQUEST_MODEl_SCHEMA, model_schema)
                self.register_route(route.view_func, route.rule_url, route.view_name, route.methods)

            self.schema["components"]["schemas"].update(definitions)

        return self.schema
