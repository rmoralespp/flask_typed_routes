import typing as t

import pydantic

import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.openapi as ftr_openapi

# Path field
a = ftr_fields.Path()
a.name = "a"
a.annotation = str
# Query field
b = ftr_fields.Query()
b.name = "b"
b.annotation = str


class QueryParams(pydantic.BaseModel):
    inner: t.Annotated[str, pydantic.Field(alias="inner-alias", max_length=3)]
    outer: t.Annotated[str, pydantic.Field(title="Outer Title", max_length=3)] = "default"


# Embedded Query field
c = ftr_fields.Query()
c.name = "c"
c.annotation = QueryParams


def test_get_parameters():
    model = pydantic.create_model("model", a=(str, ...), b=(str, ...), c=(QueryParams, ...))
    data = model.model_json_schema(ref_template=ftr_openapi.ref_template)
    fields = [a, b, c]

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
