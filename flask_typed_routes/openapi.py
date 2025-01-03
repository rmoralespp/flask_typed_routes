import collections

import pydantic

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.utils as ftr_utils

parameter_types = frozenset(
    (
        ftr_fields.FieldTypes.path,
        ftr_fields.FieldTypes.query,
        ftr_fields.FieldTypes.cookie,
        ftr_fields.FieldTypes.header,
    )
)


def duplicate_request_field(field):
    msg = f"Duplicate request parameter: [name={field.locator}, in={field.kind}]"
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
            reference = schema["$ref"].split("/")[-1].split(".")[-1]  # basename
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

                    _ = schema.pop("title", None)  # title is dont used
                    description = schema.pop("description", None)
                    examples = schema.pop("examples", ())
                    examples = {f"{name}-{i}": {"value": value} for i, value in enumerate(examples, 1)}
                    deprecated = schema.pop("deprecated", False)
                    param_spec = {
                        "name": name,
                        "in": field.kind,
                        "required": name in required,
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


def get_request_body(model_schema, fields):
    """
    Get OpenAPI operation Request body.

    :param model_schema: Python dictionary with the Pydantic JSON model schema.
    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
    :rtype: Iterable[dict]
    """

    model_properties = model_schema.get("properties", dict())
    model_required = frozenset(model_schema.get("required", ()))

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
                    if name in model_required:
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
            if name in model_required:
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
                },
            },
        }
    elif schema_ref:
        examples = schema_ref.pop("examples", ())
        examples = {f"example-{i}": {"value": value} for i, value in enumerate(examples, 1)}
        return {
            "required": required,
            "content": {
                "application/json": {
                    "schema": schema_ref,
                    "examples": examples,
                },
            },
        }
    else:
        return None


def get_route_paths(func, rule, endpoint, methods):
    """Get OpenAPI path specifications of a typed route."""

    model = getattr(func, ftr_utils.TYPED_ROUTE_MODEL, None)
    fields = getattr(func, ftr_utils.TYPED_ROUTE_FIELDS, None)
    rule_path = ftr_utils.format_openapi_path(rule)

    paths = collections.defaultdict(dict)
    schemas = dict()

    if model and fields:
        ref_template = "#/components/schemas/{endpoint}.{{model}}".format(endpoint=endpoint)
        model_schema = model.model_json_schema(ref_template=ref_template)

        schemas = model_schema.get("$defs", dict())
        schemas = {f"{endpoint}.{name}": schema for name, schema in schemas.items()}

        parameters = get_parameters(model_schema, fields)
        request_body = get_request_body(model_schema, fields)
        summary = " ".join(word.capitalize() for word in func.__name__.split("_") if word)

        spec = {
            "parameters": tuple(parameters),
            "description": ftr_utils.cleandoc(func),
            "operationId": endpoint,
            "summary": summary,
        }
        if request_body:
            spec["requestBody"] = request_body

        for method in methods:
            paths[rule_path][method.lower()] = spec

    return {
        "paths": dict(paths),
        "components": {"schemas": schemas},
    }
