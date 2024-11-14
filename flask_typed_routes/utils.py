import contextlib
import inspect
import typing as t

import flask_typed_routes.errors
import flask_typed_routes.fields


def check_types(func):
    """
    Check the types of the function annotations.

    :param func: Flask view function.
    :raises TypeError: When the annotation is invalid.
    """

    sig = inspect.signature(func)
    for name, tp in func.__annotations__.items():
        if name != "return" and is_annotated(tp):
            tp, *meta = t.get_args(tp)
            if not meta or len(meta) > 1 or not isinstance(meta[0], flask_typed_routes.fields.Field):
                raise flask_typed_routes.errors.InvalidParameterTypeError(f"Invalid annotation for {name!r} in {func.__name__!r}")
            else:
                field = meta[0]
                param = sig.parameters[name]
                if param.default != inspect.Parameter.empty and field.field_info.default is not flask_typed_routes.fields.Undef:
                    if param.default != field.field_info.default:
                        raise flask_typed_routes.errors.InvalidParameterTypeError(
                            f"Default value mismatch for {name!r} in {func.__name__!r}"
                        )

                if isinstance(field, flask_typed_routes.fields.Path) and field.alias and field.alias != name:
                    raise flask_typed_routes.errors.InvalidParameterTypeError(
                        f"Unsupported alias for Path field {name!r} in {func.__name__!r}"
                    )


def make_field(tp, field_class, is_required, default):
    if is_annotated(tp):
        # When the type is annotated, get the field from the annotation.
        tp, *meta = t.get_args(tp)
        field = meta[0]
        field.set_default(is_required, default)
        return (tp, field)
    else:
        # Otherwise, create a new field instance.
        return (tp, field_class(default=... if is_required else default))


def is_subclass(x, y):
    with contextlib.suppress(TypeError):
        return issubclass(x, y)
    return False


def is_annotated(tp):
    return t.get_origin(tp) is t.Annotated


def pretty_errors(fields, errors):
    """
    Convert the errors to a more readable format.

    :param dict fields: Field aliases
    :param Iterable[dict] errors: Pydantic validation errors
    """

    for error in errors:
        loc = list(error["loc"])
        name = loc[0]
        klass, field = fields[name]
        if field.alias:
            # If the field has an alias, use "kind", "alias", and the rest of the location.
            loc = [field.kind, name] + loc[1:]
        else:
            # Otherwise, use "kind" and the rest of the location.
            loc = [field.kind] + loc[1:]
        error["loc"] = loc
    return errors
