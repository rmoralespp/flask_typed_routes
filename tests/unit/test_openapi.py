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
    outer: t.Annotated[str, pydantic.Field(title="Outer Title", max_length=3)] = "default"


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
            'description': 'A',
            'in': 'path',
            'name': 'a',
            'required': True,
            'schema': {'type': 'string'},
        },
        {
            'description': 'B',
            'in': 'query',
            'name': 'b',
            'required': True,
            'schema': {'type': 'string'},
        },
        {
            'description': 'B1',
            'in': 'query',
            'name': 'b1',
            'required': True,
            'schema': {'type': 'string'},
            'deprecated': True,
        },
        {
            'description': 'Inner-Alias',
            'in': 'query',
            'name': 'inner-alias',
            'required': True,
            'schema': {'maxLength': 3, 'type': 'string'},
        },
        {
            'description': 'Outer Title',
            'in': 'query',
            'name': 'outer',
            'required': False,
            'schema': {'maxLength': 3, 'type': 'string', 'default': 'default'},
        },
    )
    result = tuple(ftr_openapi.get_parameters(data, fields))
    assert result == expected


def test_get_request_body_body_field():
    model = pydantic.create_model(
        "model",
        e=(Client, ...),
    )
    data = model.model_json_schema(ref_template=ftr_openapi.ref_template)
    fields = [body_field]

    expected = {
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/Client'},
            },
        },
        'description': 'Request Body',
        'required': True,
    }
    result = ftr_openapi.get_request_body(data, fields)
    assert result == expected


def test_get_request_body_embed_body_field():
    model = pydantic.create_model(
        "model",
        d=(str, None),
        f=(User, ...),
        g=(Client, ...),
    )
    data = model.model_json_schema(ref_template=ftr_openapi.ref_template)
    fields = [single_body_field, embed_body_field1, embed_body_field2]

    expected = {
        'content': {
            'application/json': {
                'schema': {
                    "type": "object",
                    "properties": {
                        'd': {'type': 'string', 'description': 'D', 'default': None},
                        'f': {'$ref': '#/components/schemas/User'},
                        'g': {'$ref': '#/components/schemas/Client'},
                    },
                    "required": ['f', 'g'],
                },
            },
        },
        'description': 'Request Body',
        'required': True,
    }
    result = ftr_openapi.get_request_body(data, fields)
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


def test_get_request_body_refs_yields_single_ref():
    request_body = {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Example"}}}}
    result = list(ftr_openapi.get_request_body_refs(request_body))
    assert result == ["#/components/schemas/Example"]


def test_get_request_body_refs_yields_multiple_refs():
    request_body = {
        "content": {
            "application/json": {
                "schema": {
                    "properties": {
                        "field1": {"$ref": "#/components/schemas/Example1"},
                        "field2": {"$ref": "#/components/schemas/Example2"},
                    }
                }
            }
        }
    }
    result = list(ftr_openapi.get_request_body_refs(request_body))
    assert result == ["#/components/schemas/Example1", "#/components/schemas/Example2"]


def test_get_request_body_refs_handles_no_refs():
    request_body = {
        "content": {
            "application/json": {
                "schema": {"properties": {"field1": {"type": "string"}, "field2": {"type": "integer"}}}
            }
        }
    }
    result = list(ftr_openapi.get_request_body_refs(request_body))
    assert result == []


def test_get_request_body_refs_handles_mixed_refs():
    request_body = {
        "content": {
            "application/json": {
                "schema": {
                    "properties": {
                        "field1": {"$ref": "#/components/schemas/Example1"},
                        "field2": {"type": "integer"},
                    }
                }
            }
        }
    }
    result = list(ftr_openapi.get_request_body_refs(request_body))
    assert result == ["#/components/schemas/Example1"]
