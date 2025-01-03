import collections
import dataclasses
import typing as t

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


class Operation(pydantic.BaseModel):
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

    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
    :param model_properties:
    :param model_components:
    :param model_required_fields:

    :rtype: Iterable[dict]
    """

    params = collections.defaultdict(dict)
    params_fields = (field for field in fields if field.kind in parameter_types)
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
        config = {
            "schema": schema_ref,
        }
        if examples:
            config["examples"] = examples
        return {
            "required": required,
            "content": {"application/json": config},
        }
    else:
        return None


def get_route_paths(func, rule, endpoint, methods):
    """Get OpenAPI path specifications of a typed route."""

    model = getattr(func, ftr_utils.TYPED_ROUTE_MODEL, None)
    fields = getattr(func, ftr_utils.TYPED_ROUTE_FIELDS, None)
    override_spec = getattr(func, ftr_utils.TYPED_ROUTE_OPENAPI, None)

    rule_path = ftr_utils.format_openapi_path(rule)

    paths = collections.defaultdict(dict)
    model_components = dict()

    if model and fields:
        ref_template = "#/components/schemas/{endpoint}.{{model}}".format(endpoint=endpoint)
        model_schema = model.model_json_schema(ref_template=ref_template)
        model_properties = model_schema.get("properties", dict())
        model_components = model_schema.get("$defs", dict())
        model_components = {f"{endpoint}.{name}": schema for name, schema in model_components.items()}
        model_required_fields = frozenset(model_schema.get("required", ()))

        parameters = get_parameters(fields, model_properties, model_components, model_required_fields)
        request_body = get_request_body(fields, model_properties, model_required_fields)

        summary = " ".join(word.capitalize() for word in func.__name__.split("_") if word)
        spec = {
            "parameters": tuple(parameters),
            "description": ftr_utils.cleandoc(func),
            "operationId": endpoint,
            "summary": summary,
        }
        if request_body:
            spec["requestBody"] = request_body
        if override_spec:
            spec.update(override_spec.model_dump(exclude_unset=True, exclude_defaults=True, exclude_none=True))
        for method in methods:
            paths[rule_path][method.lower()] = spec

    return {
        "paths": dict(paths),
        "components": {"schemas": model_components},
    }
