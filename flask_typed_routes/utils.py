import contextlib
import inspect
import re
import typing as t

import flask
import flask.views

import flask_typed_routes.errors as flask_tpr_errors
import flask_typed_routes.fields as flask_tpr_fields

# RegExp for extracting parameters from the route.
rule_regex = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def check_param_annotation(func_name, default, name, tp, /):
    """
    Check the annotation of a function parameter.
    Raise an exception if the annotation is invalid.
    """

    if is_annotated(tp):
        tp, *meta = t.get_args(tp)

        if not meta or len(meta) > 1 or not isinstance(meta[0], flask_tpr_fields.Field):
            msg = f"Invalid annotation for {name!r} in {func_name!r}"
            raise flask_tpr_errors.InvalidParameterTypeError(msg)
        else:
            field = meta[0]
            if default != inspect.Parameter.empty and field.field_info.default is not flask_tpr_fields.Undef:
                if default != field.field_info.default:
                    msg = f"Default value mismatch for {name!r} in {func_name!r}"
                    raise flask_tpr_errors.InvalidParameterTypeError(msg)

            if isinstance(field, flask_tpr_fields.Path) and field.alias and field.alias != name:
                msg = f"Unsupported alias for Path field {name!r} in {func_name!r}"
                raise flask_tpr_errors.InvalidParameterTypeError(msg)


def make_field(tp, field_class, is_required, default, /):
    if is_annotated(tp):
        # When the type is annotated, get the field from the annotation.
        tp, *meta = t.get_args(tp)
        field = meta[0]
        field.set_default(is_required, default)
        return (tp, field)
    else:
        # Otherwise, create a new field instance.
        return (tp, field_class(default=... if is_required else default))


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

    :param dict fields: Field definitions
    :param Iterable[dict] errors: Pydantic validation errors
    """

    aliases = {(field.alias or name): field for name, (_, field) in fields.items()}
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
