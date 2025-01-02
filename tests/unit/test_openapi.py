import inspect
import typing as t

import pydantic
import pytest
from typing_extensions import deprecated

import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.openapi as ftr_openapi

nondefault = inspect.Parameter.empty


class QueryParams(pydantic.BaseModel):
    inner: t.Annotated[str, pydantic.Field(alias="inner-alias", max_length=3)]
    outer: t.Annotated[str, pydantic.Field(description="Outer description", max_length=3)] = "default"


class Client(pydantic.BaseModel):
    name: str
    age: int


class User(pydantic.BaseModel):
    email: str


path_field = ftr_core.parse_field("a", str, ftr_fields.Path, nondefault)
query_field = ftr_core.parse_field("b", str, ftr_fields.Query, nondefault)
deprecated_query_field = ftr_core.parse_field(
    "b1", t.Annotated[str, ftr_fields.Query(deprecated=True)], ftr_fields.Query, nondefault
)
embed_query_field = ftr_core.parse_field("c", QueryParams, ftr_fields.Query, nondefault)
single_body_field = ftr_core.parse_field("d", str, ftr_fields.Body, None)
body_field = ftr_core.parse_field("e", Client, ftr_fields.Body, nondefault)
embed_body_field1 = ftr_core.parse_field(
    "f", t.Annotated[User, ftr_fields.Body(embed=True)], ftr_fields.Body, nondefault
)
embed_body_field2 = ftr_core.parse_field(
    "g", t.Annotated[User, ftr_fields.Body(embed=True)], ftr_fields.Body, nondefault
)


def test_get_parameters():
    model = pydantic.create_model(
        "model",
        a=(str, ...),
        b=(str, ...),
        b1=(t.Annotated[str, pydantic.Field(deprecated=True)], ...),
        c=(QueryParams, ...),
    )
    data = model.model_json_schema(ref_template=ftr_openapi.ref_template)
    fields = [path_field, query_field, deprecated_query_field, embed_query_field]

    expected = (
        {
            'in': 'path',
            'name': 'a',
            'required': True,
            'schema': {'type': 'string'},
        },
        {
            'in': 'query',
            'name': 'b',
            'required': True,
            'schema': {'type': 'string'},
        },
        {
            'in': 'query',
            'name': 'b1',
            'required': True,
            'schema': {'type': 'string'},
            'deprecated': True,
        },
        {
            'in': 'query',
            'name': 'inner-alias',
            'required': True,
            'schema': {'maxLength': 3, 'type': 'string'},
        },
        {
            'description': 'Outer description',
            'in': 'query',
            'name': 'outer',
            'required': False,
            'schema': {'maxLength': 3, 'type': 'string', 'default': 'default'},
        },
    )
    result = tuple(ftr_openapi.get_parameters(data, fields))
    assert result == expected


def test_request_body_multiple_body_parameters():
    model = pydantic.create_model(
        "model",
        d=(str, ...),
        e=(Client, ...),
    )
    data = model.model_json_schema(ref_template=ftr_openapi.ref_template)
    fields = [single_body_field, body_field]

    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        _ = ftr_openapi.get_request_body(data, fields)


def test_request_body_duplicate_field():
    model = pydantic.create_model(
        "model",
        d=(str, ...),
        e=(str, ...),
    )
    data = model.model_json_schema(ref_template=ftr_openapi.ref_template)
    fields = [single_body_field, single_body_field]

    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        _ = ftr_openapi.get_request_body(data, fields)
