import collections

import pydantic

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields

ref_template = "#/components/schemas/{model}"

parameter_types = (
    ftr_fields.FieldTypes.path,
    ftr_fields.FieldTypes.query,
    ftr_fields.FieldTypes.cookie,
    ftr_fields.FieldTypes.header,
)
parameter_types = frozenset(parameter_types)


def duplicate_field(field):
    msg = f"Duplicate parameter: [name={field.locator}, in={field.kind}]"
    return ftr_errors.InvalidParameterTypeError(msg)


def get_parameters(model_schema, fields):
    """
    Get OpenAPI schema Route parameters.

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
            if issubclass(field.annotation, pydantic.BaseModel):
                names = (info.alias or name for name, info in field.annotation.model_fields.items())
            else:
                names = (field.locator,)
            for name in names:
                if name in slot:
                    raise duplicate_field(field)
                else:
                    schema = properties[name]
                    slot[name] = {
                        "name": name,
                        "description": schema.pop("title"),  # title is the description
                        "in": field.kind,
                        "required": name in required,
                        "schema": schema,
                    }

    for value in params.values():
        yield from value.values()


def get_request_body(model_schema, fields):
    """
    Get OpenAPI schema Request Body.

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
                raise ftr_errors.InvalidParameterTypeError("Multiple body parameters")
            elif field.embed:
                if field.locator in schema_obj:
                    raise duplicate_field(field)
                else:
                    # FIXME: title ?
                    schema_obj[field.locator] = properties[field.locator]
                    if field.locator in required:
                        schema_obj_req.append(field.locator)
            elif schema_obj:
                raise ftr_errors.InvalidParameterTypeError("Multiple body parameters")
            else:
                schema_ref = properties[field.locator]

        elif field.locator in schema_obj:
            raise duplicate_field(field)
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
