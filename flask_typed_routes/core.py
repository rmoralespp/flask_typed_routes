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


def inspect_route(view_func, view_path_args, /):
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
        if isinstance(klass, str):
            # https://docs.pydantic.dev/latest/internals/resolving_annotations/
            klass = eval(klass, view_func.__globals__)

        func_alias = f"{view_func.__module__}.{view_func.__name__}"
        utils.check_param_annotation(func_alias, param.default, name, klass)
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
                # When the parameter is a Pydantic model, use alias if 'embed' is True.
                field.alias = (field.alias or name) if field.embed else None
            else:
                # Otherwise, use the alias if it is set, otherwise use the name.
                field.alias = field.alias or name

        fields[name] = (klass, field)
    return fields


def get_request_values(fields, /):
    """Get the request values from the field definitions."""

    result = dict()
    for name, (_klass, field) in fields.items():
        value = field.value
        if value is not flask_tpr_fields.Unset:
            result[field.alias or name] = value
    return result


def typed_route(view_func, rule_params, /):
    """
    A decorator that validates the request parameters using Pydantic models.

    :param view_func: Flask view function
    :param Sequence[str] rule_params: Parameters of the route rule
    :return: Decorated function
    """

    @functools.wraps(view_func)
    def decorator(*args, **kwargs):
        if fields := view_func.__flask_tpr_fields__:
            # Get request values from the fields and validate them.
            field_values = get_request_values(fields)
            try:
                instance = view_func.__flask_tpr_validator__.model_validate(field_values)
            except pydantic.ValidationError as e:
                errors = utils.pretty_errors(fields, e.errors())
                raise flask_tpr_errors.ValidationError(errors) from None
            else:
                inject = {k: getattr(instance, k) for k in fields}
                kwargs.update(inject)
                return view_func(*args, **kwargs)
        else:
            # No fields to validate, just call the view function.
            return view_func(*args, **kwargs)

    # Check the types of the function annotations before returning the decorator.
    func_fields = inspect_route(view_func, rule_params)
    # Create a Pydantic model from the field definitions.
    definitions = {name: (klass, field.field_info) for name, (klass, field) in func_fields.items()}
    if definitions:
        model_name = f"{view_func.__module__}_{view_func.__name__}_validator"
        model_name = model_name.replace(".", "_")
        view_func.__flask_tpr_fields__ = func_fields
        view_func.__flask_tpr_validator__ = pydantic.create_model(model_name, **definitions)
        # remove the temporary variables from the function
        del func_fields
        del definitions
        return decorator
    else:
        return view_func
