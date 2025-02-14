# -*- coding: utf-8 -*-

import inspect
import unittest.mock

import pydantic
import pytest

import flask_typed_routes.app as ftr_app
import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields

empty = inspect.Parameter.empty


def use_typed(a: int, c: int, b: int = 0):  # pragma: no cover
    pass


def used_non_typed(a, b):  # pragma: no cover
    pass


def use_empty():  # pragma: no cover
    pass


def use_return() -> int:  # pragma: no cover
    pass


def test_get_request_values():
    fields = [
        unittest.mock.Mock(value=1, locator="a"),
        unittest.mock.Mock(value=ftr_fields.Unset, locator="b"),
    ]
    expected = {"a": 1}
    result = ftr_core.get_request_values(fields)
    assert result == expected


@pytest.mark.parametrize("fields", [[unittest.mock.Mock(value=ftr_fields.Unset, locator="b")], []])
def test_get_request_values_empty(fields):
    result = ftr_core.get_request_values(fields)
    expected = dict()
    assert result == expected


def test_get_request_values_duplicate_locator():
    fields = [
        unittest.mock.Mock(value=1, locator="a"),
        unittest.mock.Mock(value=2, locator="a"),
    ]
    expected = {"a": 2}
    result = ftr_core.get_request_values(fields)
    assert result == expected


@pytest.mark.parametrize("name", ["name", "", None])
def test_set_field_alias_path(name):
    field = ftr_fields.Path(alias="ignored_alias")
    field.name = name
    result = ftr_core.set_field_alias(field)
    assert result.alias == name


def test_set_field_alias_body_embed():
    field = ftr_fields.Body(embed=True, alias="used_alias")
    field.annotation = pydantic.create_model("Model", a=(int, ...))
    result = ftr_core.set_field_alias(field)
    assert result.alias == "used_alias"


@pytest.mark.parametrize("embed", [False, None])
def test_set_field_alias_body_no_embed(embed):
    field = ftr_fields.Body(embed=embed, alias="ignored_alias")
    field.annotation = pydantic.create_model("Model", a=(int, ...))
    result = ftr_core.set_field_alias(field)
    assert result.alias is None  # check is None explicitly


@pytest.mark.parametrize("name, ini_alias, expected", [
    ("name", "alias", "alias"),  # prefer alias
    (None, "alias", "alias"),  # prefer alias
    ("name", None, "name"),  # use name
    (None, None, None),
])
@pytest.mark.parametrize("field_class", [ftr_fields.Query, ftr_fields.Cookie, ftr_fields.Header])
def test_set_field_alias_query_cookie_header(field_class, name, ini_alias, expected):
    field = field_class(alias=ini_alias)
    field.name = name
    result = ftr_core.set_field_alias(field)
    assert result.alias == expected


@unittest.mock.patch.object(ftr_core, "set_field_alias")
def test_set_field_props(set_field_alias):
    field = unittest.mock.Mock()
    result = ftr_core.set_field_props(field, "name", int, 1)
    field.name = "name"
    field.annotation = int
    field.default = 1
    set_field_alias.assert_called_once_with(field)
    assert result == set_field_alias.return_value


def test_resolve_field_params_typed():
    result = ftr_core.resolve_field_params(use_typed, "my_view", ("a",))

    first = next(result)
    second = next(result)
    third = next(result)
    fourth = next(result, None)

    # Assert first parameter
    assert isinstance(first, ftr_fields.Path)
    assert first.name == "a"
    assert first.annotation is int
    assert first.default == ftr_fields.Undef

    # Assert second parameter
    assert isinstance(second, ftr_fields.Query)
    assert second.name == "c"
    assert second.annotation is int
    assert second.default == ftr_fields.Undef

    # Assert third parameter
    assert isinstance(third, ftr_fields.Query)
    assert third.name == "b"
    assert third.annotation is int
    assert third.default == 0

    # Assert fourth parameter
    assert fourth is None


@pytest.mark.parametrize("view_func", [used_non_typed, use_empty, use_return])
def test_resolve_field_params_empty(view_func):
    result = ftr_core.resolve_field_params(view_func, "my_view", ())
    assert tuple(result) == ()


def test_create_model_typed():
    model, _ = ftr_core.create_model(use_typed, "my_view", ("a", "c"))
    model_fields = {
        name: dict(annotation=info.annotation, default=info.default, alias=info.alias)
        for name, info in model.model_fields.items()
    }
    expected_model_fields = {
        'a': dict(annotation=int, default=ftr_fields.Undef, alias='a'),
        'b': dict(annotation=int, default=0, alias='b'),
        'c': dict(annotation=int, default=ftr_fields.Undef, alias='c')
    }
    assert issubclass(model, pydantic.BaseModel)
    assert model.__name__ == "my_view"
    assert model_fields == expected_model_fields


@pytest.mark.parametrize("view_func", [used_non_typed, use_empty, use_return])
def test_create_model_none(view_func):
    result = ftr_core.create_model(view_func, "my_view", ())
    assert result == (None, None)


def test_resolve_field_params_non_typed():
    dependencies = [ftr_fields.Depends(unittest.mock.Mock())]
    fn = ftr_app.typed_route(dependencies=dependencies)(used_non_typed)
    result = ftr_core.resolve_non_returning_dependencies(fn, "my_view")
    assert result == dependencies


def test_resolve_field_params_no_dependencies_fail():
    dependencies = [unittest.mock.Mock()]
    fn = ftr_app.typed_route(dependencies=dependencies)(used_non_typed)
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        ftr_core.resolve_non_returning_dependencies(fn, "my_view")
