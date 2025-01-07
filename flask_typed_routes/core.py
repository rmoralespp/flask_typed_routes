import functools
import inspect
import typing as t

import pydantic

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.utils as ftr_utils


def get_request_values(fields, /):
    """
    Get the request values from the field definitions.

    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
    :rtype: dict[str, Any]
    """

    result = dict()
    for field in fields:
        value = field.value  # use variable to avoid multiple calls to the property
        if value is not ftr_fields.Unset:
            result[field.locator] = value
    return result


def parse_field(name, tp, default_field_class, default_value, /):
    """
    Parse the field definition from the type annotation.

    :param name: Parameter name
    :param tp: Type Annotation
    :param default_field_class: Default field class to use when the type is not annotated.
    :param default_value: Parameter default value
    :rtype: flask_typed_routes.fields.Field
    """

    if ftr_utils.is_annotated(tp):
        # When the type is annotated, get the field from the annotation.
        original_tp = tp
        tp, *metalist = t.get_args(original_tp)
        field = next((m for m in metalist if isinstance(m, ftr_fields.Field)), default_field_class())
        field_info = pydantic.fields.FieldInfo.from_annotation(original_tp)
        # Later `FieldInfo` instances override earlier ones.
        # Prioritize the `Field` above any other metadata
        field.field_info = pydantic.fields.FieldInfo.merge_field_infos(field_info, field.field_info)
    else:
        # Otherwise, create a new field instance.
        field = default_field_class()

    # Set the field properties.
    field.default = default_value
    field.annotation = tp
    field.name = name

    # Set the alias property based on the field type.
    if isinstance(field, ftr_fields.Path):
        # Respect the name of the path parameter offered by `Flask` routing.
        field.alias = name
    elif ftr_utils.is_subclass(field.annotation, pydantic.BaseModel):
        # When the parameter is a Pydantic model, use alias if `embed` is True.
        field.alias = field.locator if field.embed else None
    else:
        # Otherwise, use the alias if it is set, otherwise use the name.
        field.alias = field.locator
    return field


def parse_route(view_func, view_func_path, view_path_args, /):
    """
    Return field definitions for the view function annotations.

    :param view_func: Flask view function
    :param view_func_path: Path to the view function
    :param view_path_args: Parameters of the route rule
    :rtype: Generator[flask_tpr_fields.Field]
    """

    sig = inspect.signature(view_func)
    annotations = ftr_utils.get_annotations(view_func, view_func_path)
    for name, annotation in annotations.items():
        if name == "return":
            continue  # Skip the return annotation

        param = sig.parameters[name]
        ftr_utils.validate_field_annotation(view_func_path, param.default, name, annotation)

        if ftr_utils.is_subclass(annotation, pydantic.BaseModel):  # Request body
            field_class = ftr_fields.Body
        elif name in view_path_args:  # Path parameter
            field_class = ftr_fields.Path
        else:  # Query parameter by default
            field_class = ftr_fields.Query
        yield parse_field(name, annotation, field_class, param.default)


def route(view_func, rule_params, /):
    """
    A decorator that validates the request parameters using Pydantic models.

    :param view_func: Flask view function
    :param Sequence[str] rule_params: Parameters of the route rule
    :return: Decorated function
    """

    @functools.wraps(view_func)
    def decorator(*args, **kwargs):
        values = get_request_values(fields)
        try:
            instance = model.model_validate(values)
        except pydantic.ValidationError as e:
            errors = ftr_utils.pretty_errors(fields, e.errors())
            raise ftr_errors.ValidationError(errors) from None
        else:
            inject = {field.name: getattr(instance, field.name) for field in fields}
            kwargs.update(inject)
            return view_func(*args, **kwargs)

    # Check the types of the function annotations before returning the decorator.
    view_func_path = ftr_utils.get_func_path(view_func)
    fields = tuple(parse_route(view_func, view_func_path, rule_params))
    # Create a Pydantic model from the field definitions.
    definitions = {field.name: (field.annotation, field.field_info) for field in fields}
    if definitions:
        model_name = f"{view_func_path}.request_model"
        model_name = model_name.replace(".", "__")
        model = pydantic.create_model(model_name, **definitions)

        setattr(decorator, ftr_utils.TYPED_ROUTE_REQUEST_MODEL, model)
        setattr(decorator, ftr_utils.TYPED_ROUTE_PARAM_FIELDS, fields)
        return decorator
    else:
        return view_func
