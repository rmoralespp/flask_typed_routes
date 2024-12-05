import inspect
import typing as t

import flask.views
import pydantic
import pytest

import flask_typed_routes.errors as flask_tpr_errors
import flask_typed_routes.fields as flask_tpr_fields
import flask_typed_routes.utils as utils


@pytest.mark.parametrize(
    "annotation, default, field, expected_error",
    [
        # Nested meta annotation
        (
            t.Annotated[t.Annotated[int, flask_tpr_fields.Path()], flask_tpr_fields.Path()],
            inspect.Parameter.empty,
            "param",
            flask_tpr_errors.InvalidParameterTypeError,
        ),
        # Multiple meta annotations
        (
            t.Annotated[int, flask_tpr_fields.Path(), flask_tpr_fields.Path()],
            inspect.Parameter.empty,
            "param",
            flask_tpr_errors.InvalidParameterTypeError,
        ),
        # Non-field meta annotation
        (
            t.Annotated[int, "not_a_field"],
            inspect.Parameter.empty,
            "param",
            flask_tpr_errors.InvalidParameterTypeError,
        ),
        # Default value mismatch
        (
            t.Annotated[int, flask_tpr_fields.Path(default=1)],
            2,
            "param",
            flask_tpr_errors.InvalidParameterTypeError,
        ),
        # Unsupported Path alias
        (
            t.Annotated[int, flask_tpr_fields.Path(alias="different_name")],
            inspect.Parameter.empty,
            "param",
            flask_tpr_errors.InvalidParameterTypeError,
        ),
    ],
)
def test_check_param_annotation_raises_error(annotation, default, field, expected_error):
    with pytest.raises(expected_error):
        utils.check_param_annotation("func", default, field, annotation)


@pytest.mark.parametrize(
    "annotation, default, field",
    [
        # Valid non-annotated annotation
        (int, inspect.Parameter.empty, "param"),
        # Valid non-annotated annotation with default value
        (int, 1, "param"),
        # Valid annotated annotation
        (
            t.Annotated[int, flask_tpr_fields.Path()],
            inspect.Parameter.empty,
            "param",
        ),
        # Matching annotated annotation with default value
        (
            t.Annotated[int, flask_tpr_fields.Path(default=1)],
            1,
            "param",
        ),
        # Path field without alias
        (
            t.Annotated[int, flask_tpr_fields.Path()],
            inspect.Parameter.empty,
            "param",
        ),
    ],
)
def test_check_param_annotation_passes(annotation, default, field):
    utils.check_param_annotation("func", default, field, annotation)


@pytest.mark.parametrize(
    "annotation, default_field_class, default_value, expected_tp, expected_default, expected_field_class",
    [
        # Test case: Optional Annotated annotation
        (
            t.Annotated[int, flask_tpr_fields.Header()],
            flask_tpr_fields.Query,
            "default",
            int,
            "default",
            flask_tpr_fields.Header,
        ),
        # Test case: Required Annotated annotation
        (
            t.Annotated[int, flask_tpr_fields.Header()],
            flask_tpr_fields.Query,
            inspect.Parameter.empty,
            int,
            flask_tpr_fields.Undef,
            flask_tpr_fields.Header,
        ),
        # Test case: Required annotation
        (
            int,
            flask_tpr_fields.Query,
            inspect.Parameter.empty,
            int,
            flask_tpr_fields.Undef,
            flask_tpr_fields.Query,
        ),
        # Test case: Optional annotation
        (
            int,
            flask_tpr_fields.Query,
            "default",
            int,
            "default",
            flask_tpr_fields.Query,
        ),
        # Test case: Nested Annotated annotation
        (
            t.Annotated[t.Annotated[int, flask_tpr_fields.Header()], flask_tpr_fields.Header()],
            flask_tpr_fields.Query,
            "default",
            int,
            "default",
            flask_tpr_fields.Header,
        ),
    ],
)
def test_parse_field(
    annotation, default_field_class, default_value, expected_tp, expected_default, expected_field_class
):
    field = utils.parse_field("fieldname", annotation, default_field_class, default_value)
    assert field.field_info.default == expected_default
    assert field.annotation == expected_tp
    assert field.name == "fieldname"
    assert isinstance(field, expected_field_class)


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

    field = utils.parse_field("name", Model, flask_tpr_fields.JsonBody, None)
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
