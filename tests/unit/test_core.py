import inspect
import typing as t

import annotated_types as at
import pydantic
import pytest

import flask_typed_routes.core as ftr_core
import flask_typed_routes.fields as ftr_fields

empty = inspect.Parameter.empty


@pytest.mark.parametrize(
    "annotation, default_field_class, default_value, expected_tp, expected_default, expected_field_cls, expected_alias",
    [
        # Test case: Optional Annotated annotation
        (
            t.Annotated[int, pydantic.Field(default=..., alias="foo"), ftr_fields.Header(alias="alias_name")],
            ftr_fields.Query,
            "default",
            int,
            "default",
            ftr_fields.Header,
            "alias_name",
        ),
        # Test case: Required Annotated annotation
        (
            t.Annotated[int, ftr_fields.Header()],
            ftr_fields.Query,
            empty,
            int,
            ftr_fields.Undef,
            ftr_fields.Header,
            "fieldname",
        ),
        # Test case: Required annotation
        (
            int,
            ftr_fields.Query,
            empty,
            int,
            ftr_fields.Undef,
            ftr_fields.Query,
            "fieldname",
        ),
        # Test case: Optional annotation
        (
            int,
            ftr_fields.Query,
            "default",
            int,
            "default",
            ftr_fields.Query,
            "fieldname",
        ),
        # Test case: Nested Annotated annotation
        (
            t.Annotated[t.Annotated[int, pydantic.Field(alias="foo")], ftr_fields.Path(alias="foo")],
            ftr_fields.Query,
            "default",
            int,
            "default",
            ftr_fields.Path,
            "fieldname",
        ),
        # Test case: Pydantic custom type
        (
            pydantic.NonNegativeInt,
            ftr_fields.Query,
            empty,
            int,
            ftr_fields.Undef,
            ftr_fields.Query,
            "fieldname",
        ),
        # Test case: Pydantic custom type combined with Annotated
        (
            t.Annotated[pydantic.NonNegativeInt, at.Gt(10), pydantic.Field(default=..., alias="alias_name")],
            ftr_fields.Query,
            1,
            int,
            1,
            ftr_fields.Query,
            "alias_name",
        ),
        # Test case: Annotated type with multiple annotations
        (
            t.Annotated[int, at.Gt(10), at.Lt(20), at.MultipleOf(2)],
            ftr_fields.Query,
            1,
            int,
            1,
            ftr_fields.Query,
            "fieldname",
        ),
    ],
)
def test_parse_field(
    annotation, default_field_class, default_value, expected_tp, expected_default, expected_field_cls, expected_alias
):
    field = ftr_core.parse_field("fieldname", annotation, default_field_class, default_value)
    assert isinstance(field, expected_field_cls)
    assert field.default == expected_default
    assert field.annotation == expected_tp
    assert field.name == "fieldname"
    assert field.alias == expected_alias
