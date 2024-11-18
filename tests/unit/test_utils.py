import inspect
import typing as t

import flask.views
import pytest

import flask_typed_routes.errors as flask_tpr_errors
import flask_typed_routes.fields as flask_tpr_fields
import flask_typed_routes.utils as utils


def test_check_param_annotation_raises_error_for_multiple_meta():
    with pytest.raises(flask_tpr_errors.InvalidParameterTypeError):
        utils.check_param_annotation(
            "func",
            inspect.Parameter.empty,
            "param",
            t.Annotated[int, flask_tpr_fields.Path(), flask_tpr_fields.Path()]
        )


def test_check_param_annotation_raises_error_for_non_field_meta():
    with pytest.raises(flask_tpr_errors.InvalidParameterTypeError):
        utils.check_param_annotation("func", inspect.Parameter.empty, "param", t.Annotated[int, "not_a_field"])


def test_check_param_annotation_raises_error_for_default_value_mismatch():
    field = flask_tpr_fields.Path(default=1)
    with pytest.raises(flask_tpr_errors.InvalidParameterTypeError):
        utils.check_param_annotation("func", 2, "param", t.Annotated[int, field])


def test_check_param_annotation_raises_error_for_unsupported_alias():
    field = flask_tpr_fields.Path(alias="different_name")
    with pytest.raises(flask_tpr_errors.InvalidParameterTypeError):
        utils.check_param_annotation("func", inspect.Parameter.empty, "param", t.Annotated[int, field])


def test_check_param_annotation_passes_for_valid_annotation():
    field = flask_tpr_fields.Path()
    utils.check_param_annotation("func", inspect.Parameter.empty, "param", t.Annotated[int, field])


def test_check_param_annotation_passes_for_matching_default_value():
    field = flask_tpr_fields.Path(default=1)
    utils.check_param_annotation("func", 1, "param", t.Annotated[int, field])


def test_check_param_annotation_passes_for_path_field_without_alias():
    field = flask_tpr_fields.Path()
    utils.check_param_annotation("func", inspect.Parameter.empty, "param", t.Annotated[int, field])


def test_test_make_field_with_optional_annotation():
    default = object()
    tp, field = utils.make_field(t.Annotated[int, flask_tpr_fields.Header()], flask_tpr_fields.Query, False, default)
    assert tp is int
    assert field.field_info.default == default
    assert isinstance(field, flask_tpr_fields.Header)


def test_make_field_with_required_annotation():
    # When the annotation is required, the default value is ignored.
    default = object()
    tp, field = utils.make_field(t.Annotated[int, flask_tpr_fields.Header()], flask_tpr_fields.Query, True, default)
    assert tp is int
    assert field.field_info.default == flask_tpr_fields.Undef
    assert isinstance(field, flask_tpr_fields.Header)


def test_make_required_field_without_annotation():
    default = object()
    tp, field = utils.make_field(int, flask_tpr_fields.Query, True, default)
    assert tp is int
    assert field.field_info.default == flask_tpr_fields.Undef
    assert isinstance(field, flask_tpr_fields.Query)


def test_make_optional_field_without_annotation():
    default = object()
    tp, field = utils.make_field(int, flask_tpr_fields.Query, False, default)
    assert tp is int
    assert field.field_info.default == default
    assert isinstance(field, flask_tpr_fields.Query)


def test_is_subclass_valid():
    assert utils.is_subclass(int, object)


def test_is_subclass_invalid():
    assert not utils.is_subclass(int, str)


def test_is_annotated_true():
    assert utils.is_annotated(t.Annotated[int, flask_tpr_fields.Path()])


def test_is_annotated_false():
    assert not utils.is_annotated(int)


def test_pretty_errors_with_alias():
    fields = {"name": (str, flask_tpr_fields.Path(alias="alias_name"))}
    errors = [{"loc": ["name"]}]
    result = utils.pretty_errors(fields, errors)
    assert result[0]["loc"] == ['path', 'name']


def test_pretty_errors_without_alias():
    fields = {"name": (str, flask_tpr_fields.JsonBody())}
    errors = [{"loc": ["name"]}]
    result = utils.pretty_errors(fields, errors)
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


@pytest.mark.parametrize("view, expected", [
    (MockView(), ValidView),  # Caso válido
    (InvalidView(), None),  # Clase de vista no válida
    (NoViewClass(), None),  # Sin atributo view_class
    (object(), None),  # Objeto simple
    (None, None),  # None como entrada
])
def test_class_based_view(view, expected):
    assert utils.class_based_view(view) == expected
