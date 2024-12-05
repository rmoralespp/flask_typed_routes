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
    Return field definitions for the view function annotations.

    :param view_func: Flask view function
    :param view_path_args: Parameters of the route rule
    :rtype: Generator[flask_tpr_fields.Field]
    """

    sig = inspect.signature(view_func)
    for name, annotation in view_func.__annotations__.items():
        if name == "return":
            continue  # Skip the return annotation

        param = sig.parameters[name]
        if isinstance(annotation, str):
            # https://docs.pydantic.dev/latest/internals/resolving_annotations/
            annotation = eval(annotation, view_func.__globals__)

        func_path = f"{view_func.__module__}.{view_func.__name__}"
        utils.check_param_annotation(func_path, param.default, name, annotation)

        if utils.is_subclass(annotation, pydantic.BaseModel):  # Request body
            field_class = flask_tpr_fields.JsonBody
        elif name in view_path_args:  # Path parameter
            field_class = flask_tpr_fields.Path
        else:  # Query parameter by default
            field_class = flask_tpr_fields.Query

        yield utils.parse_field(name, annotation, field_class, param.default)


def get_request_values(fields, /):
    """
    Get the request values from the field definitions.

    :param Iterable[flask_tpr_fields.Field] fields: Field definitions
    :rtype: dict[str, Any]
    """

    result = dict()
    for field in fields:
        value = field.value  # use variable to avoid multiple calls to the property
        if value is not flask_tpr_fields.Unset:
            result[field.alias or field.name] = value
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
        fields = view_func.__flask_tpr_fields__
        values = get_request_values(fields)
        try:
            instance = view_func.__flask_tpr_validator__.model_validate(values)
        except pydantic.ValidationError as e:
            errors = utils.pretty_errors(fields, e.errors())
            raise flask_tpr_errors.ValidationError(errors) from None
        else:
            inject = {field.name: getattr(instance, field.name) for field in fields}
            kwargs.update(inject)
            return view_func(*args, **kwargs)

    # Check the types of the function annotations before returning the decorator.
    route_fields = tuple(inspect_route(view_func, rule_params))
    # Create a Pydantic model from the field definitions.
    definitions = {field.name: (field.annotation, field.field_info) for field in route_fields}
    if definitions:
        model_name = f"{view_func.__module__}_{view_func.__name__}_validator"
        model_name = model_name.replace(".", "_")
        view_func.__flask_tpr_fields__ = route_fields
        view_func.__flask_tpr_validator__ = pydantic.create_model(model_name, **definitions)
        return decorator
    else:
        return view_func
