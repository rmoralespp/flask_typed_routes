import collections
import itertools

import pydantic

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
    msg = "Duplicate request parameter: [name=%s, in=%s]"
    ftr_utils.logger.warning(msg, field.locator, field.kind)


def duplicate_request_body():
    ftr_utils.logger.warning("Duplicate request body")


def get_summary(operation_id, /):
    """Get the summary for the OpenAPI operation."""

    return " ".join(word.capitalize() for word in operation_id.split("_") if word)


def merge_parameters(a, b, /):
    """Merge two OpenAPI operation parameters."""

    bag = set()
    for param in itertools.chain(a, b):
        key = param["$ref"] if "$ref" in param else (param["name"] + param["in"])
        if key not in bag:
            bag.add(key)
            yield param


def get_parameters(fields, model_properties, model_required_fields, definitions, /):
    """
    Get OpenAPI operation parameters for given fields.

    :param Iterable[flask_typed_routes.Field] fields: Field definitions.
    :param dict[str, dict] model_properties: Schema properties.
    :param Sequence[str] model_required_fields: Schema required fields.
    :param dict[str, dict] definitions: Models definitions.
    :rtype: Iterable[dict]
    """

    params = collections.defaultdict(dict)
    params_fields = (field for field in fields if field.kind in PARAMETER_TYPES)
    for field in params_fields:
        slot = params[field.kind]
        if ftr_utils.is_subclass(field.annotation, pydantic.BaseModel):
            ref_properties = model_properties[field.locator]
            ref_name = ref_properties["$ref"].split("/")[-1]
            ref_schema = definitions[ref_name]
            properties_slot = ref_schema.get("properties", dict())
            required_slot = frozenset(ref_schema.get("required", ()))
            names = (info.alias or name for name, info in field.annotation.model_fields.items())
        else:
            properties_slot = model_properties
            required_slot = model_required_fields
            names = (field.locator,)

        for name in names:
            if name in slot:
                duplicate_request_field(field)
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

                # Get the extra JSON schema properties
                if "style" in schema:
                    param_spec["style"] = schema.pop("style")
                if "explode" in schema:
                    param_spec["explode"] = schema.pop("explode")
                if "allowReserved" in schema:
                    param_spec["allowReserved"] = schema.pop("allowReserved")
                slot[name] = param_spec

    for value in params.values():
        yield from value.values()


def get_unvalidated_parameters(path_args):
    """
    Get OpenAPI operation parameters for unvalidated route.

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

    :param dict[str, dict] model_properties: Schema properties.
    :param Sequence[str] model_required_fields: Schema required fields.

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
            duplicate_request_body()
        elif issubclass(field.annotation, pydantic.BaseModel):
            if field.embed and name in schema_obj:
                duplicate_request_field(field)
            elif field.embed:
                schema_obj[name] = model_properties[name]
                if name in model_required_fields:
                    required_fields.append(name)
            elif schema_obj:
                duplicate_request_body()
            else:
                schema_ref = model_properties[name]
                required = field.is_required
        elif name in schema_obj:
            duplicate_request_field(field)
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


class OpenApi:

    def __init__(
        self,
        *,
        title: str = "API doc",
        version: str = "0.0.1",  # This is the version of your application
        openapi_version: str = "3.1.0",
        summary: str = None,
        description: str = None,
        terms_of_service: str = None,
        contact_info: dict = None,
        license_info: dict = None,
        servers: list[dict] = None,
        webhooks: dict[str, dict] = None,
        components: dict = None,
        tags: list[dict] = None,
        external_docs: dict = None,
    ):
        """OpenAPI generator for Flask Typed Routes views."""

        self.title = title
        self.version = version
        self.openapi_version = openapi_version
        self.summary = summary
        self.description = description
        self.terms_of_service = terms_of_service
        self.contact_info = contact_info
        self.license_info = license_info
        self.servers = servers
        self.webhooks = webhooks
        self.components = components
        self.tags = tags
        self.external_docs = external_docs
        # Calculated attributes
        self.paths = collections.defaultdict(dict)

    @staticmethod
    def get_route_operations(route, error_status_code, model_schema, definitions, /):
        """
        Get OpenAPI operations for a route.

        :param flask_typed_routes.utils.RouteInfo route: Route to get operations.
        :param int error_status_code: Status code for validation errors response.
        :param Optional[dict] model_schema: Route Model schema.
        :param dict[str, dict] definitions: Models definitions.
        :rtype dict:
        """

        param_fields = getattr(route.func, ftr_utils.ROUTE_PARAM_FIELDS, None)
        status_code = getattr(route.func, ftr_utils.ROUTE_STATUS_CODE, None)

        spec = getattr(route.func, ftr_utils.ROUTE_OPENAPI, dict())

        parameters = spec.pop("parameters", ())
        responses = spec.pop("responses", dict())
        description = spec.pop("description", ftr_utils.cleandoc(route.func))
        request_body = spec.pop("requestBody", None)
        operation_id = spec.pop("operationId", None)
        summary = spec.pop("summary", None)

        result = collections.defaultdict(dict)
        path = ftr_utils.format_openapi_path(route.rule)
        status_code = status_code or "default"

        if model_schema and param_fields:
            required_fields = frozenset(model_schema.get("required", ()))
            properties = model_schema.get("properties", dict())
            model_parameters = get_parameters(param_fields, properties, required_fields, definitions)
            parameters = tuple(merge_parameters(parameters, model_parameters))
            request_body = request_body or get_request_body(param_fields, properties, required_fields)
            responses = {
                str(error_status_code): HTTP_VALIDATION_ERROR_REF,
                str(status_code): HTTP_SUCCESS_RESPONSE,
                **responses,
            }
        else:
            # Unvalidated parameters for the route.
            unvalidated_parameters = tuple(get_unvalidated_parameters(route.args))
            parameters = tuple(merge_parameters(parameters, unvalidated_parameters))
            responses = {str(status_code): HTTP_SUCCESS_RESPONSE, **responses}

        for method in route.methods:
            method = method.lower()
            # Include the method in the operation ID to avoid conflicts with other operations
            method_id = operation_id or f"{route.name}_{method}"
            method_summary = summary or get_summary(method_id)
            operation = {
                **spec,
                "operationId": method_id,
                "summary": method_summary,
                "description": description,
                "parameters": parameters,
                "responses": responses,
            }
            if request_body:
                operation["requestBody"] = request_body
            result[path][method] = operation

        return result

    def register_route(self, route, error_status_code, model_schema, definitions, /):
        """
        Register a route in the OpenAPI schema document.

        :param flask_typed_routes.utils.RouteInfo route: Route to register.
        :param int error_status_code: Status code for validation errors response.
        :param Optional[dict] model_schema: Route Model schema.
        :param dict[str, dict] definitions: Models definitions.
        """

        paths = self.get_route_operations(
            route,
            error_status_code,
            model_schema,
            definitions,
        )
        for path, spec in paths.items():
            self.paths[path].update(spec)

    @staticmethod
    def models_json_schema(models):
        validation_models = zip(models, itertools.repeat("validation"))
        validation_models = tuple(validation_models)
        ref_template = REF_PREFIX + "{model}"
        return pydantic.json_schema.models_json_schema(validation_models, ref_template=ref_template)

    @classmethod
    def routes_json_schema(cls, routes):
        models_by_route = []
        models = []
        for route in routes:
            model = getattr(route.func, ftr_utils.ROUTE_REQUEST_MODEL, None)
            models_by_route.append((route, model))
            if model:
                models.append(model)

        if models:
            schemas_map, schemas_defs = cls.models_json_schema(models)
            definitions = schemas_defs["$defs"]
            # Add the validation error schemas to the definitions
            definitions.update(
                {
                    VALIDATION_ERROR_KEY: VALIDATION_ERROR_DEF,
                    HTTP_VALIDATION_ERROR_KEY: HTTP_VALIDATION_ERROR_DEF,
                }
            )
        else:
            schemas_map = dict()
            definitions = dict()
        return (schemas_map, definitions, models_by_route)

    def get_schema(self, routes, error_status_code):
        """
        Get the OpenAPI schema document based on the registered routes.

        :param Iterable[flask_typed_routes.utils.RouteInfo] routes: Registered routes.
        :param int error_status_code: Status code for validation errors response.
        :rtype: dict
        """

        info = {"title": self.title, "version": self.version}
        if self.summary:
            info["summary"] = self.summary
        if self.description:
            info["description"] = self.description
        if self.terms_of_service:
            info["termsOfService"] = self.terms_of_service
        if self.contact_info:
            info["contact"] = self.contact_info
        if self.license_info:
            info["license"] = self.license_info

        result = {
            "openapi": self.openapi_version,
            "info": info,
            "paths": self.paths,
            "components": dict(),
        }
        schemas = dict()
        if self.servers:
            result["servers"] = self.servers
        if self.webhooks:
            result["webhooks"] = self.webhooks
        if self.components:
            # Extract the schemas of the provided components to merge them later.
            # These schemas take precedence over the schemas of the models
            schemas = self.components.pop("schemas", dict())
            result["components"].update(self.components)
        if self.tags:
            result["tags"] = self.tags
        if self.external_docs:
            result["externalDocs"] = self.external_docs

        # Register the routes inspects the view functions and extracts the model schemas.
        schemas_map, definitions, models_by_route = self.routes_json_schema(routes)
        for route, model in models_by_route:
            if model:
                # Get the function model schema from the definitions and remove it.
                model_schema_ref = schemas_map[(model, "validation")]["$ref"]
                model_schema_ref = model_schema_ref.split("/")[-1]  # basename
                model_schema = definitions.pop(model_schema_ref)
            else:
                model_schema = None
            self.register_route(route, error_status_code, model_schema, definitions)

        # Update the definitions with the given schemas, given schemas have higher priority
        # Finally, add merged schemas to the OpenApi components.
        schemas = {**definitions, **schemas}
        if schemas:
            result["components"]["schemas"] = schemas
        return result
