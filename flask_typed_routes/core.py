# -*- coding: utf-8 -*-

import functools
import inspect
import typing as t

import pydantic

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.utils as ftr_utils


def get_request_values(fields, /):
    result = dict()
    for field in fields:
        value = field.value  # use variable to avoid multiple calls to the property
        if value is not ftr_fields.Unset:
            result[field.locator] = value
    return result


def set_field_alias(field, /):
    # +ATTENTION+: The 'field' must have an 'annotation' and 'name' attributes set.

    if isinstance(field, ftr_fields.Path | ftr_fields.Depends):
        # Respect the name of the path parameter offered by `Flask` routing.
        # Also, respect the name of the dependency parameter.
        field.alias = field.name
    elif field.is_model_object:
        # When the object parameter is a Pydantic model, use alias if `embed` is True.
        field.alias = field.locator if field.embed else None
    else:
        # Otherwise, use the alias if it is set, otherwise use the name.
        field.alias = field.locator
    return field


def set_field_props(field, name, tp, default_value, /):
    field.name = name
    field.annotation = tp
    field.default = default_value
    return set_field_alias(field)


def resolve_annotated_field(tp, default_field_class, /):
    original_tp = tp
    tp, *metalist = t.get_args(original_tp)
    field = next((m for m in metalist if isinstance(m, ftr_fields.Field)), default_field_class())
    field_info = pydantic.fields.FieldInfo.from_annotation(original_tp)
    # Later `FieldInfo` instances override earlier ones.
    # Prioritize the `Field` above any other metadata
    field.field_info = pydantic.fields.FieldInfo.merge_field_infos(field_info, field.field_info)
    return (field, tp)


def resolve_field(name, tp, is_path_field, default_value, /):
    if is_path_field:  # Path parameter
        klass = ftr_fields.Path
    elif ftr_utils.is_subclass(tp, pydantic.BaseModel):  # Request body
        klass = ftr_fields.Body
    else:  # Query parameter by default
        klass = ftr_fields.Query

    if ftr_utils.is_annotated(tp):
        field, tp = resolve_annotated_field(tp, klass)
    else:
        field = klass()
    return set_field_props(field, name, tp, default_value)


def resolve_field_params(view_func, view_name, view_args, /):
    sig = inspect.signature(view_func)
    parameters = sig.parameters
    annotations = ftr_utils.get_annotations(view_func, view_name)
    for name, annotation in annotations.items():
        if name != "return":
            default = parameters[name].default
            ftr_utils.validate_field_annotation(view_name, default, name, annotation)
            is_path_arg = name in view_args
            yield resolve_field(name, annotation, is_path_arg, default)


def create_model(view_func, view_name, view_args, /):
    """Create a Pydantic model from the view function annotations."""

    fields = tuple(resolve_field_params(view_func, view_name, view_args))
    definitions = {field.name: (field.annotation, field.field_info) for field in fields}
    if definitions:
        model = pydantic.create_model(view_name, **definitions)
        return (model, fields)
    else:
        return (None, None)


def resolve_non_returning_dependencies(view_func, view_name, /):
    """
    Resolve the dependencies of the view function.
    :param view_func:
    :param view_name:
    :rtype: Sequence[flask_typed_routes.fields.Depends]
    """

    result = getattr(view_func, ftr_utils.ROUTE_DEPENDENCIES, ()) or ()
    if not all(isinstance(d, ftr_fields.Depends) for d in result):
        msg = f"The dependencies must be of type 'Depends' in {view_name!r}"
        raise ftr_errors.InvalidParameterTypeError(msg)
    return result


def validate(view_func, view_name, view_args, /):
    """
    A decorator that validates the request parameters of the view function.

    :param view_func: Flask view function.
    :param str view_name: Unique Name of the view function.
    :param Sequence[str] view_args: Arguments of the view function.
    """

    @functools.wraps(view_func)
    def decorator(*args, **kwargs):
        # Calls the dependencies before the model validation.
        for dependency in dependencies:
            _ = dependency.value  # Ensure that the dependency is called.
        if model and fields:
            try:
                instance = model.model_validate(get_request_values(fields))
            except pydantic.ValidationError as e:
                errors = ftr_utils.pretty_errors(fields, e.errors(include_context=False))
                raise ftr_errors.ValidationError(errors) from None
            else:
                inject = ((field.name, getattr(instance, field.name)) for field in fields)
                kwargs.update(inject)
        return view_func(*args, **kwargs)

    dependencies = resolve_non_returning_dependencies(view_func, view_name)
    model, fields = create_model(view_func, view_name, view_args)
    if (model and fields) or dependencies:
        setattr(decorator, ftr_utils.ROUTE_REQUEST_MODEL, model)
        setattr(decorator, ftr_utils.ROUTE_PARAM_FIELDS, fields)
        return decorator
    else:
        return view_func
