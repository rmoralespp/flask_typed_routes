"""
Contains the main application logic.
Offers a decorator to validate the request parameters using Pydantic models.
"""

import functools
import inspect

import pydantic

import flask_typed_routes.errors as flask_tpr_errors
import flask_typed_routes.fields as flask_tpr_fields
import flask_typed_routes.utils as utils


def inspect_route(view_func, view_path_args):
    """
    Return pydantic field definitions for the view function annotations.

    :param view_func: Flask view function
    :param view_path_args: Parameters of the route rule
    :return: Dict of field definitions
    """

    sig = inspect.signature(view_func)
    fields = dict()

    for name, klass in view_func.__annotations__.items():
        if name == "return":
            continue  # Skip the return annotation

        param = sig.parameters[name]

        func_dir = f"{view_func.__module__}.{view_func.__name__}"
        utils.check_param_annotation(func_dir, param.default, name, klass)
        is_required = param.default == inspect.Parameter.empty

        if utils.is_subclass(klass, pydantic.BaseModel):  # Request body
            field = flask_tpr_fields.JsonBody(default=... if is_required else param.default)
            field.alias = None  # No alias for the request body
        elif name in view_path_args:  # Path parameter
            klass, field = utils.make_field(
                klass,
                flask_tpr_fields.Path,
                is_required,
                param.default,
            )
            field.alias = name  # Respect name offered by Flask
        else:  # Query parameter by default
            klass, field = utils.make_field(
                klass,
                flask_tpr_fields.Query,
                is_required,
                param.default,
            )
            if utils.is_subclass(klass, pydantic.BaseModel):
                # When the parameter is a Pydantic model, use alias if embed is True.
                field.alias = (field.alias or name) if field.embed else None
            else:
                # Otherwise, use the alias if it is set, otherwise use the name.
                field.alias = field.alias or name

        fields[name] = (klass, field)
    return fields


def get_request_values(fields):
    """Get the request values from the field definitions."""

    values = dict()
    for name, (_klass, field) in fields.items():
        value = field.value
        if value is not flask_tpr_fields.Unset:
            values[field.alias or name] = value
    return values


def typed_route(view_func, rule_params):
    """
    A decorator that validates the request parameters using Pydantic models.

    :param view_func: Flask view function
    :param Sequence[str] rule_params: Parameters of the route rule
    :return: Decorated function
    """

    @functools.wraps(view_func)
    def decorator(*args, **kwargs):
        # Get request values from the field definitions.
        field_values = get_request_values(fields)
        if field_values:
            try:
                instance = model.model_validate(field_values)
            except pydantic.ValidationError as e:
                errors = utils.pretty_errors(fields_aliases, e.errors())
                raise flask_tpr_errors.ValidationError(errors) from None
            else:
                inject = {k: getattr(instance, k) for k in fields}
                kwargs.update(inject)
                return view_func(*args, **kwargs)
        else:
            # No fields to validate, just call the view function.
            return view_func(*args, **kwargs)

    # Check the types of the function annotations before returning the decorator.
    fields = inspect_route(view_func, rule_params)
    fields_definitions = dict()
    fields_aliases = dict()
    for name, (klass, field) in fields.items():
        fields_definitions[name] = (klass, field.field_info)
        fields_aliases[field.alias or name] = (klass, field)

    if fields_definitions:
        model_name = f"{view_func.__module__}_{view_func.__name__}_validator"
        model_name = model_name.replace(".", "_")
        model = pydantic.create_model(model_name, **fields_definitions)
        return decorator
    else:
        return view_func
