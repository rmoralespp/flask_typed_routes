import inspect
import typing as t

import annotated_types as at
import flask.views
import pydantic
import pytest

import flask_typed_routes.errors as flask_tpr_errors
import flask_typed_routes.fields as flask_tpr_fields
import flask_typed_routes.utils as utils

empty = inspect.Parameter.empty


@pytest.mark.parametrize(
    "annotation, default",
    [
        # 'Path' must be at the end of the annotation list
        (t.Annotated[int, flask_tpr_fields.Path(), at.Gt(10)], empty),
        # Multiple field annotations
        (t.Annotated[int, flask_tpr_fields.Path(), flask_tpr_fields.Path()], empty),
        # Default value mismatch
        (t.Annotated[int, flask_tpr_fields.Path(default=1)], 2),
        # Unsupported Path alias
        (t.Annotated[int, flask_tpr_fields.Path(alias="different_name")], empty),
    ],
)
def test_check_param_annotation_raises_error(annotation, default):
    with pytest.raises(flask_tpr_errors.InvalidParameterTypeError):
        utils.check_param_annotation("func", default, "param", annotation)


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
        (t.Annotated[int, flask_tpr_fields.Path()], empty),
        # Matching annotated annotation with default value
        (t.Annotated[int, flask_tpr_fields.Path(default=1)], 1),
        # Path field without alias
        (t.Annotated[int, flask_tpr_fields.Path()], empty),
        # Pydantic custom types
        (pydantic.NonNegativeInt, empty),
        # Pydantic custom types combined with Annotated
        (t.Annotated[pydantic.NonNegativeInt, at.Gt(10)], 20),
        # Mixed Annotated types
        (t.Annotated[int, at.Gt(10), flask_tpr_fields.Path()], empty),
    ],
)
def test_check_param_annotation_passes(annotation, default):
    utils.check_param_annotation("func", default, "param", annotation)


@pytest.mark.parametrize(
    "annotation, default_field_class, default_value, expected_tp, expected_default, expected_field_cls, expected_alias",
    [
        # Test case: Optional Annotated annotation
        (
            t.Annotated[int, pydantic.Field(default=..., alias="foo"), flask_tpr_fields.Header(alias="alias_name")],
            flask_tpr_fields.Query,
            "default",
            int,
            "default",
            flask_tpr_fields.Header,
            "alias_name",
        ),
        # Test case: Required Annotated annotation
        (
            t.Annotated[int, flask_tpr_fields.Header()],
            flask_tpr_fields.Query,
            empty,
            int,
            flask_tpr_fields.Undef,
            flask_tpr_fields.Header,
            "fieldname",
        ),
        # Test case: Required annotation
        (
            int,
            flask_tpr_fields.Query,
            empty,
            int,
            flask_tpr_fields.Undef,
            flask_tpr_fields.Query,
            "fieldname",
        ),
        # Test case: Optional annotation
        (
            int,
            flask_tpr_fields.Query,
            "default",
            int,
            "default",
            flask_tpr_fields.Query,
            "fieldname",
        ),
        # Test case: Nested Annotated annotation
        (
            t.Annotated[t.Annotated[int, pydantic.Field(alias="foo")], flask_tpr_fields.Path(alias="foo")],
            flask_tpr_fields.Query,
            "default",
            int,
            "default",
            flask_tpr_fields.Path,
            "fieldname",
        ),
        # Test case: Pydantic custom type
        (
            pydantic.NonNegativeInt,
            flask_tpr_fields.Query,
            empty,
            int,
            flask_tpr_fields.Undef,
            flask_tpr_fields.Query,
            "fieldname",
        ),
        # Test case: Pydantic custom type combined with Annotated
        (
            t.Annotated[pydantic.NonNegativeInt, at.Gt(10), pydantic.Field(default=..., alias="alias_name")],
            flask_tpr_fields.Query,
            1,
            int,
            1,
            flask_tpr_fields.Query,
            "alias_name",
        ),
        # Test case: Annotated type with multiple annotations
        (
            t.Annotated[int, at.Gt(10), at.Lt(20), at.MultipleOf(2)],
            flask_tpr_fields.Query,
            1,
            int,
            1,
            flask_tpr_fields.Query,
            "fieldname",
        ),
    ],
)
def test_parse_field(
    annotation, default_field_class, default_value, expected_tp, expected_default, expected_field_cls, expected_alias
):
    field = utils.parse_field("fieldname", annotation, default_field_class, default_value)
    assert isinstance(field, expected_field_cls)
    assert field.default == expected_default
    assert field.annotation == expected_tp
    assert field.name == "fieldname"
    assert field.alias == expected_alias


def test_is_subclass_valid():
    assert utils.is_subclass(int, object)


def test_is_subclass_invalid():
    assert not utils.is_subclass(int, str)


def test_is_annotated_true():
    assert utils.is_annotated(t.Annotated[int, flask_tpr_fields.Path()])


def test_is_annotated_false():
    assert not utils.is_annotated(int)


def test_pretty_errors_with_alias():
    field = utils.parse_field(
        "name",
        t.Annotated[str, flask_tpr_fields.Query(alias="alias_name")],
        flask_tpr_fields.Query,
        None,
    )
    errors = [{"loc": ["alias_name"]}]
    result = utils.pretty_errors([field], errors)
    assert result[0]["loc"] == ['query', 'alias_name']


def test_pretty_errors_without_alias():
    class Model(pydantic.BaseModel):
        age: str

    field = utils.parse_field("name", Model, flask_tpr_fields.Body, None)
    errors = [{"loc": ["name"]}]
    result = utils.pretty_errors([field], errors)
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
    result = utils.extract_rule_params(rule)
    assert result == expected


# Caso 1: Clase de vista válida
class ValidView(flask.views.View):
    def dispatch_request(self):
        return "Valid View"


class MockView:
    view_class = ValidView


# Caso 2: Clase de vista no válida
class NotAFlaskView:
    pass


class InvalidView:
    view_class = NotAFlaskView


# Caso 3: Objeto sin atributo view_class
class NoViewClass:
    pass


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
    assert utils.class_based_view(view) == expected
