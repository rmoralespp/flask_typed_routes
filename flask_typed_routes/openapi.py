import collections

import pydantic

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.utils as ftr_utils

ref_template = "#/components/schemas/{model}"

parameter_types = (
    ftr_fields.FieldTypes.path,
    ftr_fields.FieldTypes.query,
    ftr_fields.FieldTypes.cookie,
    ftr_fields.FieldTypes.header,
)
parameter_types = frozenset(parameter_types)


def duplicate_request_field(field):
    msg = f"Duplicate parameter: [name={field.locator}, in={field.kind}]"
    return ftr_errors.InvalidParameterTypeError(msg)


def duplicate_request_body():
    return ftr_errors.InvalidParameterTypeError("Duplicate request body")


def get_parameters(model_schema, fields):
    """
    Get OpenAPI operation parameters.

    :param model_schema: Python dictionary with the Pydantic JSON model schema.
    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
    :rtype: Iterable[dict]
    """

    required = set(model_schema.get("required", ()))
    components = model_schema.get("$defs", dict())
    properties = dict()

    for name, schema in model_schema.get("properties", dict()).items():
        if "$ref" in schema:
            reference = schema["$ref"].split("/")[-1]  # basename
            component = components[reference]
            if name in required:
                required.remove(name)
            required.update(component.get("required", ()))
            properties.update(component["properties"])
        else:
            properties[name] = schema

    params = collections.defaultdict(dict)
    for field in fields:
        if field.kind in parameter_types:
            slot = params[field.kind]
            if ftr_utils.is_subclass(field.annotation, pydantic.BaseModel):
                names = (info.alias or name for name, info in field.annotation.model_fields.items())
            else:
                names = (field.locator,)
            for name in names:
                if name in slot:
                    raise duplicate_request_field(field)
                else:
                    schema = properties[name]
                    title = schema.pop("title")
                    description = schema.pop("description", title)
                    example_values = schema.pop("examples", ())
                    param_spec = {
                        "name": name,
                        "description": description,
                        "deprecated": schema.pop("deprecated", False),
                        "in": field.kind,
                        "required": name in required,
                        "schema": schema,
                        # "allowEmptyValue": False,  # TODO: Implement!!, use official default value
                    }
                    if example_values:
                        examples = {f"{name}-{value}": {"value": value} for i, value in enumerate(example_values)}
                        param_spec["examples"] = examples
                    slot[name] = param_spec

    for value in params.values():
        yield from value.values()


def get_request_body(model_schema, fields):
    """
    Get OpenAPI operation Request body.

    :param model_schema: Python dictionary with the Pydantic JSON model schema.
    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
    :rtype: Iterable[dict]
    """

    properties = model_schema.get("properties", dict())
    schema_ref = dict()
    schema_obj = dict()
    schema_obj_req = []
    required = frozenset(model_schema.get("required", ()))
    body_fields = (field for field in fields if field.kind == ftr_fields.FieldTypes.body)
    for field in body_fields:
        if issubclass(field.annotation, pydantic.BaseModel):
            if schema_ref:
                raise duplicate_request_body()
            elif field.embed:
                if field.locator in schema_obj:
                    raise duplicate_request_field(field)
                else:
                    # FIXME: title ?
                    schema_obj[field.locator] = properties[field.locator]
                    if field.locator in required:
                        schema_obj_req.append(field.locator)
            elif schema_obj:
                raise duplicate_request_body()
            else:
                schema_ref = properties[field.locator]

        elif field.locator in schema_obj:
            raise duplicate_request_field(field)
        else:
            schema_field = properties[field.locator]
            schema_field["description"] = schema_field.pop("title")  # title is the description
            schema_obj[field.locator] = schema_field
            if field.locator in required:
                schema_obj_req.append(field.locator)

    if schema_ref:
        schema = {
            "description": "Request Body",
            "required": True,
            "content": {"application/json": {"schema": schema_ref}},
        }
    elif schema_obj:
        schema = {
            "description": "Request Body",
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": schema_obj,
                        "required": schema_obj_req,
                    },
                },
            },
        }
    else:
        schema = None
    return schema


def get_request_body_refs(request_body):
    schema = request_body["content"]["application/json"]["schema"]
    if "$ref" in schema:
        yield schema["$ref"]
    else:
        for field in schema.get("properties", dict()).values():
            if "$ref" in field:
                yield field["$ref"]


def get_components(request_body_refs, model_schema):
    components = model_schema.get("$defs", dict())
    for ref in request_body_refs:
        reference = ref.split("/")[-1]  # basename
        yield (reference, components[reference])


def get_route_paths(func, rule, endpoint, methods):
    """Get OpenAPI path specifications of a typed route."""

    model = getattr(func, ftr_utils.TYPED_ROUTE_MODEL, None)
    fields = getattr(func, ftr_utils.TYPED_ROUTE_FIELDS, None)
    path = ftr_utils.rule_regex.sub(r"{\1}", rule)

    result = {
        "schemas": dict(),
        "paths": collections.defaultdict(dict),
    }

    if model and fields:
        model_schema = model.model_json_schema(ref_template=ref_template)

        parameters = get_parameters(model_schema, fields)
        request_body = get_request_body(model_schema, fields)

        spec = {
            "parameters": tuple(parameters),
            "summary": func.__doc__,
            "description": func.__doc__,
            "operationId": endpoint,
        }
        if request_body:
            schemas = get_components(get_request_body_refs(request_body), model_schema)
            result["schemas"] = dict(schemas)
            spec["requestBody"] = request_body

        for method in methods:
            result["paths"][path][method.lower()] = spec

    return result
