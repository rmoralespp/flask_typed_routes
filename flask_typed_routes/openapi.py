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


def get_parameters(data, fields):
    """
    Get OpenAPI schema Route parameters.

    :param data: Python dictionary with the Pydantic model schema.
    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
    :return:
    """

    required = set(data.get("required", ()))
    definitions = data.get("$defs", dict())
    schemas = dict()
    for name, schema in data["properties"].items():
        if "$ref" in schema:
            reference = schema["$ref"].split("/")[-1]  # basename
            definition = definitions[reference]
            if name in required:
                required.remove(name)
            required.update(definition.get("required", ()))
            schemas.update(definition["properties"])
        else:
            schemas[name] = schema

    params = collections.defaultdict(dict)
    for field in fields:
        if field.kind in parameter_types:
            slot = params[field.kind]

            if issubclass(field.annotation, pydantic.BaseModel):
                names = [info.alias or name for name, info in field.annotation.model_fields.items()]
            else:
                names = [field.locator]
            for name in names:
                if name in slot:
                    msg = f"Duplicate parameter: [name={name}, in={field.kind}]"
                    raise ftr_errors.InvalidParameterTypeError(msg)
                else:
                    schema = schemas[name]
                    slot[name] = {
                        "name": name,
                        "description": schema.pop("title"),
                        "in": field.kind,
                        "required": name in required,
                        "schema": schema,
                    }

    for _, value in params.items():
        for _, schema in value.items():
            yield schema
