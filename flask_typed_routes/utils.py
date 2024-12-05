import contextlib
import inspect
import re
import typing as t

import flask
import flask.views
import pydantic

import flask_typed_routes.errors as flask_tpr_errors
import flask_typed_routes.fields as flask_tpr_fields

# RegExp for extracting parameters from the route.
rule_regex = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def check_param_annotation(func_path, default, name, tp, /):
    """
    Check the annotation of a function parameter.
    Raise an exception if the annotation is invalid.
    """

    if is_annotated(tp):
        tp, *metalist = t.get_args(tp)
        field = None
        empty = inspect.Parameter.empty

        for meta in metalist:
            if isinstance(meta, flask_tpr_fields.Field):
                if field:
                    msg = f"Multiple field annotations for {name!r} in {func_path!r}"
                    raise flask_tpr_errors.InvalidParameterTypeError(msg)
                else:
                    field = meta

                if default != empty and field.default is not flask_tpr_fields.Undef and default != field.default:
                    msg = f"Default value mismatch for {name!r} in {func_path!r}"
                    raise flask_tpr_errors.InvalidParameterTypeError(msg)

                if isinstance(field, flask_tpr_fields.Path) and field.alias and field.alias != name:
                    msg = f"Unsupported alias for Path field {name!r} in {func_path!r}"
                    raise flask_tpr_errors.InvalidParameterTypeError(msg)

            elif field:
                msg = "'Field' must be at the end of the annotation list."
                raise flask_tpr_errors.InvalidParameterTypeError(msg)


def parse_field(name, tp, default_field_class, default_value, /):
    """
    Parse the field definition from the type annotation.

    :param name: Parameter name
    :param tp: Type Annotation
    :param default_field_class: Default field class to use when the type is not annotated.
    :param default_value: Parameter default value
    :rtype: flask_tpr_fields.Field
    """

    if is_annotated(tp):
        # When the type is annotated, get the field from the annotation.
        original_tp = tp
        tp, *metalist = t.get_args(original_tp)
        field = next((m for m in metalist if isinstance(m, flask_tpr_fields.Field)), default_field_class())
        field_info = pydantic.fields.FieldInfo.from_annotation(original_tp)
        # Later `FieldInfo` instances override earlier ones.
        # Prioritize the "flask_tpr_fields.Field" field above any other metadata
        field.field_info = pydantic.fields.FieldInfo.merge_field_infos(field_info, field.field_info)
    else:
        # Otherwise, create a new field instance.
        field = default_field_class()

    # Set the field properties.
    field.default = default_value
    field.annotation = tp
    field.name = name

    # Set the alias property based on the field type.
    if is_subclass(field.annotation, pydantic.BaseModel):
        # When the parameter is a Pydantic model, use alias if 'embed' is True.
        field.alias = (field.alias or field.name) if field.embed else None
    elif isinstance(field, flask_tpr_fields.Path):
        # Respect the name of the path parameter offered by Flask routing.
        field.alias = name
    else:
        # Otherwise, use the alias if it is set, otherwise use the name.
        field.alias = field.alias or field.name
    return field


def is_subclass(x, y, /):
    with contextlib.suppress(TypeError):
        return issubclass(x, y)
    return False


def class_based_view(view, /):
    klass = getattr(view, "view_class", None)
    return klass if klass and is_subclass(klass, flask.views.View) else None


def is_annotated(tp, /):
    return t.get_origin(tp) is t.Annotated


def pretty_errors(fields, errors, /):
    """
    Convert the errors to a more readable format.

    :param Iterable[flask_tpr_fields.Field] fields: Field definitions
    :param Iterable[dict] errors: Pydantic validation errors
    :rtype: list[dict]
    """

    aliases = {(field.alias or field.name): field for field in fields}
    for error in errors:
        loc = list(error["loc"])
        field = aliases[loc[0]]
        if field.alias:
            # If the field has an alias, use "kind", "alias", and the rest of the location.
            loc = [field.kind, field.alias] + loc[1:]
        else:
            # Otherwise, use "kind" and the rest of the location.
            loc = [field.kind] + loc[1:]
        error["loc"] = loc
    return errors


def extract_rule_params(rule, /):
    return frozenset(rule_regex.findall(rule))
