"""
Contains the main application logic.
Offers a decorator to validate the request parameters using Pydantic models.
"""

import functools
import inspect

import pydantic

import flask_typed_routes.errors
import flask_typed_routes.fields
import flask_typed_routes.utils


def inspect_route(view_func, view_kwargs):
    """Return pydantic field definitions for the view function annotations."""

    sig = inspect.signature(view_func)
    fields = dict()
    values = dict(**view_kwargs)

    for name, klass in view_func.__annotations__.items():
        if name == "return":
            continue

        param = sig.parameters[name]
        is_required = param.default == inspect.Parameter.empty

        if flask_typed_routes.utils.is_subclass(klass, pydantic.BaseModel):  # Request body
            field = flask_typed_routes.fields.JsonBody(default=... if is_required else param.default)
            field.alias = None  # No alias for the request body
        elif name in view_kwargs:  # Path parameter
            klass, field = flask_typed_routes.utils.make_field(klass, flask_typed_routes.fields.Path, is_required, param.default)
            field.alias = name  # Respect name offered by Flask
        else:  # Query parameter by default
            klass, field = flask_typed_routes.utils.make_field(klass, flask_typed_routes.fields.Query, is_required, param.default)
            if flask_typed_routes.utils.is_subclass(klass, pydantic.BaseModel):
                # When the parameter is a Pydantic model, use alias if embed is True.
                field.alias = (field.alias or name) if field.embed else None
            else:
                # Otherwise, use the alias if it is set, otherwise use the name.
                field.alias = field.alias or name

        fields[name] = (klass, field)
        value = field.value
        if value is not flask_typed_routes.fields.Unset:
            values[field.alias or name] = value

    return fields, values


def typed_route(func):
    """
    A decorator that validates the request parameters using Pydantic models.

    :param func: Flask view function
    :return: Decorated function
    """

    @functools.wraps(func)
    def decorator(*args, **kwargs):
        fields, values = inspect_route(func, kwargs)
        fields_definitions = dict()
        fields_aliases = dict()
        for name, (klass, field) in fields.items():
            fields_definitions[name] = (klass, field.field_info)
            fields_aliases[field.alias or name] = (klass, field)

        model = pydantic.create_model("TypedRouteModel", **fields_definitions)
        try:
            instance = model.model_validate(values)
        except pydantic.ValidationError as e:
            errors = flask_typed_routes.utils.pretty_errors(fields_aliases, e.errors())
            raise flask_typed_routes.errors.ValidationError(errors) from None
        else:
            inject = {k: getattr(instance, k) for k in fields}
            return func(*args, **inject)

    # Check the types of the function annotations before returning the decorator.
    flask_typed_routes.utils.check_types(func)
    return decorator
