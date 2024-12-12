import inspect
import typing as t

import annotated_types as at
import flask.views
import pydantic
import pydantic.fields
import pytest

import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.utils as ftr_utils

empty = inspect.Parameter.empty


class MyClass:
    def my_method(self):
        pass

    @staticmethod
    def my_staticmethod():
        pass

    @classmethod
    def my_classmethod(cls):
        pass


class ValidView(flask.views.View):
    def dispatch_request(self):
        return "Valid View"


class MockView:
    view_class = ValidView


class NotAFlaskView:
    pass


class InvalidView:
    view_class = NotAFlaskView


class NoViewClass:
    pass


@pytest.mark.parametrize(
    "annotation, default",
    [
        # 'Path' must be at the end of the annotation list
        (t.Annotated[int, ftr_fields.Path(), at.Gt(10)], empty),
        # Multiple field annotations
        (t.Annotated[int, ftr_fields.Path(), ftr_fields.Path()], empty),
        # Default value mismatch
        (t.Annotated[int, ftr_fields.Path(default=1)], 2),
    ],
)
def test_validate_field_annotation_raises_error(annotation, default):
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        ftr_utils.validate_field_annotation("func", default, "param", annotation)


@pytest.mark.parametrize(
    "annotation, default",
    [
        # Valid non-annotated annotation
        (int, empty),
        # Valid non-annotated annotation with default value
        (int, 1),
        # Valid annotated with multiple annotations
        (t.Annotated[int, at.Gt(10), at.Lt(20), at.MultipleOf(2)], empty),
        # Valid annotated annotation
        (t.Annotated[int, ftr_fields.Path()], empty),
        # Matching annotated annotation with default value
        (t.Annotated[int, ftr_fields.Path(default=1)], 1),
        # Path field without alias
        (t.Annotated[int, ftr_fields.Path()], empty),
        # Pydantic custom types
        (pydantic.NonNegativeInt, empty),
        # Pydantic custom types combined with Annotated
        (t.Annotated[pydantic.NonNegativeInt, at.Gt(10)], 20),
        # Mixed Annotated types
        (t.Annotated[int, at.Gt(10), pydantic.Field(le=20), ftr_fields.Path()], empty),
    ],
)
def test_validate_field_annotation_passes(annotation, default):
    ftr_utils.validate_field_annotation("func", default, "param", annotation)


def test_is_subclass_valid():
    assert ftr_utils.is_subclass(int, object)


def test_is_subclass_invalid():
    assert not ftr_utils.is_subclass(int, str)


def test_is_annotated_true():
    assert ftr_utils.is_annotated(t.Annotated[int, ftr_fields.Path()])


def test_is_annotated_false():
    assert not ftr_utils.is_annotated(int)


def test_pretty_errors_with_alias():
    field = ftr_core.parse_field(
        "name",
        t.Annotated[str, ftr_fields.Query(alias="alias_name")],
        ftr_fields.Query,
        None,
    )
    errors = [{"loc": ["alias_name"]}]
    result = ftr_utils.pretty_errors([field], errors)
    assert result[0]["loc"] == ['query', 'alias_name']


def test_pretty_errors_without_alias():
    class Model(pydantic.BaseModel):
        age: str

    field = ftr_core.parse_field("name", Model, ftr_fields.Body, None)
    errors = [{"loc": ["name"]}]
    result = ftr_utils.pretty_errors([field], errors)
    assert result[0]["loc"] == ["body"]


@pytest.mark.parametrize(
    "rule, expected",
    [
        ("/user/<int:id>", frozenset(["id"])),
        ("/user/<int:id>/post/<int:post_id>", frozenset(["id", "post_id"])),
        ("/user/list", frozenset()),
        ("/user/<int:id>/post/<string:title>", frozenset(["id", "title"])),
        ("/user/<path:subpath>", frozenset(["subpath"])),
        ("/user/<user_id>/details/<detail_id>", frozenset(["user_id", "detail_id"])),
    ],
)
def test_extract_rule_params(rule, expected):
    result = ftr_utils.extract_rule_params(rule)
    assert result == expected


@pytest.mark.parametrize(
    "view, expected",
    [
        (MockView(), ValidView),  # Caso válido
        (InvalidView(), None),  # Clase de vista no válida
        (NoViewClass(), None),  # Sin atributo view_class
        (object(), None),  # Objeto simple
        (None, None),  # None como entrada
    ],
)
def test_class_based_view(view, expected):
    assert ftr_utils.class_based_view(view) == expected


# Casos de prueba con pytest y parametrize
@pytest.mark.parametrize(
    "func, expected",
    [
        (ftr_utils.get_func_path, "flask_typed_routes.utils.get_func_path"),
        (MyClass.my_classmethod, "unit.test_utils.MyClass.my_classmethod"),
        (lambda: None, "unit.test_utils.<lambda>"),
        (MyClass.my_staticmethod, "unit.test_utils.MyClass.my_staticmethod"),
        (MyClass.my_staticmethod, "unit.test_utils.MyClass.my_staticmethod"),
        (MyClass.my_classmethod, "unit.test_utils.MyClass.my_classmethod"),
    ],
)
def test_get_func_path(func, expected):
    assert ftr_utils.get_func_path(func) == expected
