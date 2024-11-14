import typing as t

import pytest

import flask_typed_routes.errors
import flask_typed_routes.fields
import flask_typed_routes.utils


def test_check_types_valid_annotation():
    def func(a: t.Annotated[int, flask_typed_routes.fields.Path()]):
        pass

    flask_typed_routes.utils.check_types(func)


def test_check_types_abstract_annotation():
    msg = "Can't instantiate abstract class Field without an implementation for abstract method 'value'"
    with pytest.raises(TypeError, match=msg):

        def func(a: t.Annotated[int, flask_typed_routes.fields.Field()]):
            pass


def test_check_types_invalid_annotation():
    def func(a: t.Annotated[int, "invalid"]):
        pass

    msg = "Invalid annotation for 'a' in 'func'"
    with pytest.raises(flask_typed_routes.errors.InvalidParameterTypeError, match=msg):
        flask_typed_routes.utils.check_types(func)


def test_check_types_default_mismatch():
    def func(a: t.Annotated[int, flask_typed_routes.fields.Path(default=1)] = 2):
        pass

    msg = "Default value mismatch for 'a' in 'func'"
    with pytest.raises(flask_typed_routes.errors.InvalidParameterTypeError, match=msg):
        flask_typed_routes.utils.check_types(func)


def test_check_types_path_alias_mismatch_param_name():
    def func(a: t.Annotated[int, flask_typed_routes.fields.Path(alias="alias")]):
        pass

    msg = "Unsupported alias for Path field 'a' in 'func'"
    with pytest.raises(flask_typed_routes.errors.InvalidParameterTypeError, match=msg):
        flask_typed_routes.utils.check_types(func)


def test_make_field_with_optional_annotation():
    default = object()
    tp, field = flask_typed_routes.utils.make_field(t.Annotated[int, flask_typed_routes.fields.Header()], flask_typed_routes.fields.Query, False, default)
    assert tp is int
    assert field.field_info.default == default
    assert isinstance(field, flask_typed_routes.fields.Header)


def test_make_field_with_required_annotation():
    # When the annotation is required, the default value is ignored.
    default = object()
    tp, field = flask_typed_routes.utils.make_field(t.Annotated[int, flask_typed_routes.fields.Header()], flask_typed_routes.fields.Query, True, default)
    assert tp is int
    assert field.field_info.default == flask_typed_routes.fields.Undef
    assert isinstance(field, flask_typed_routes.fields.Header)


def test_make_required_field_without_annotation():
    default = object()
    tp, field = flask_typed_routes.utils.make_field(int, flask_typed_routes.fields.Query, True, default)
    assert tp is int
    assert field.field_info.default == flask_typed_routes.fields.Undef
    assert isinstance(field, flask_typed_routes.fields.Query)


def test_make_optional_field_without_annotation():
    default = object()
    tp, field = flask_typed_routes.utils.make_field(int, flask_typed_routes.fields.Query, False, default)
    assert tp is int
    assert field.field_info.default == default
    assert isinstance(field, flask_typed_routes.fields.Query)


def test_is_subclass_valid():
    assert flask_typed_routes.utils.is_subclass(int, object)


def test_is_subclass_invalid():
    assert not flask_typed_routes.utils.is_subclass(int, str)


def test_is_annotated_true():
    assert flask_typed_routes.utils.is_annotated(t.Annotated[int, flask_typed_routes.fields.Path()])


def test_is_annotated_false():
    assert not flask_typed_routes.utils.is_annotated(int)


def test_pretty_errors_with_alias():
    fields = {"name": (str, flask_typed_routes.fields.Path(alias="alias_name"))}
    errors = [{"loc": ["name"]}]
    result = flask_typed_routes.utils.pretty_errors(fields, errors)
    assert result[0]["loc"] == ['path', 'name']


def test_pretty_errors_without_alias():
    fields = {"name": (str, flask_typed_routes.fields.JsonBody())}
    errors = [{"loc": ["name"]}]
    result = flask_typed_routes.utils.pretty_errors(fields, errors)
    assert result[0]["loc"] == ["body"]
