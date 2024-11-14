import typing as t

import pytest

import src.errors
import src.fields
import src.utils


def test_check_types_valid_annotation():
    def func(a: t.Annotated[int, src.fields.Path()]):
        pass

    src.utils.check_types(func)


def test_check_types_abstract_annotation():
    msg = "Can't instantiate abstract class Field without an implementation for abstract method 'value'"
    with pytest.raises(TypeError, match=msg):

        def func(a: t.Annotated[int, src.fields.Field()]):
            pass


def test_check_types_invalid_annotation():
    def func(a: t.Annotated[int, "invalid"]):
        pass

    msg = "Invalid annotation for 'a' in 'func'"
    with pytest.raises(src.errors.InvalidParameterTypeError, match=msg):
        src.utils.check_types(func)


def test_check_types_default_mismatch():
    def func(a: t.Annotated[int, src.fields.Path(default=1)] = 2):
        pass

    msg = "Default value mismatch for 'a' in 'func'"
    with pytest.raises(src.errors.InvalidParameterTypeError, match=msg):
        src.utils.check_types(func)


def test_check_types_path_alias_mismatch_param_name():
    def func(a: t.Annotated[int, src.fields.Path(alias="alias")]):
        pass

    msg = "Unsupported alias for Path field 'a' in 'func'"
    with pytest.raises(src.errors.InvalidParameterTypeError, match=msg):
        src.utils.check_types(func)


def test_make_field_with_optional_annotation():
    default = object()
    tp, field = src.utils.make_field(t.Annotated[int, src.fields.Header()], src.fields.Query, False, default)
    assert tp is int
    assert field.field_info.default == default
    assert isinstance(field, src.fields.Header)


def test_make_field_with_required_annotation():
    # When the annotation is required, the default value is ignored.
    default = object()
    tp, field = src.utils.make_field(t.Annotated[int, src.fields.Header()], src.fields.Query, True, default)
    assert tp is int
    assert field.field_info.default == src.fields.Undef
    assert isinstance(field, src.fields.Header)


def test_make_required_field_without_annotation():
    default = object()
    tp, field = src.utils.make_field(int, src.fields.Query, True, default)
    assert tp is int
    assert field.field_info.default == src.fields.Undef
    assert isinstance(field, src.fields.Query)


def test_make_optional_field_without_annotation():
    default = object()
    tp, field = src.utils.make_field(int, src.fields.Query, False, default)
    assert tp is int
    assert field.field_info.default == default
    assert isinstance(field, src.fields.Query)


def test_is_subclass_valid():
    assert src.utils.is_subclass(int, object)


def test_is_subclass_invalid():
    assert not src.utils.is_subclass(int, str)


def test_is_annotated_true():
    assert src.utils.is_annotated(t.Annotated[int, src.fields.Path()])


def test_is_annotated_false():
    assert not src.utils.is_annotated(int)


def test_pretty_errors_with_alias():
    fields = {"name": (str, src.fields.Path(alias="alias_name"))}
    errors = [{"loc": ["name"]}]
    result = src.utils.pretty_errors(fields, errors)
    assert result[0]["loc"] == ['path', 'name']


def test_pretty_errors_without_alias():
    fields = {"name": (str, src.fields.JsonBody())}
    errors = [{"loc": ["name"]}]
    result = src.utils.pretty_errors(fields, errors)
    assert result[0]["loc"] == ["body"]
