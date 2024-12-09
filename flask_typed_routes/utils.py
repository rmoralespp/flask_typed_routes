import contextlib
import inspect
import re
import typing as t

import flask
import flask.views

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields

# RegExp for extracting parameters from the route.
rule_regex = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def validate_field_annotation(func_path, default, name, tp, /):
    """
    Validates the annotation of a function parameter, ensuring it is a valid field annotation.
    Raises an exception if the annotation is invalid or inconsistent with the default value.
    """

    if is_annotated(tp):
        tp, *metalist = t.get_args(tp)
        field = None
        empty = inspect.Parameter.empty

        for meta in metalist:
            if isinstance(meta, ftr_fields.Field):
                if field:
                    msg = f"Multiple field annotations for {name!r} in {func_path!r}"
                    raise ftr_errors.InvalidParameterTypeError(msg)
                else:
                    field = meta

                if default != empty and field.default is not ftr_fields.Undef and default != field.default:
                    msg = f"Default value mismatch for {name!r} in {func_path!r}"
                    raise ftr_errors.InvalidParameterTypeError(msg)

            elif field:
                msg = "'Field' must be at the end of the annotation list."
                raise ftr_errors.InvalidParameterTypeError(msg)


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

    :param Iterable[flask_typed_routes.fields.Field] fields: Field definitions
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


def get_func_path(func):
    """Get the full path of a function/method."""

    return f"{func.__module__}.{func.__qualname__}"
