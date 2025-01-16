import inspect
import unittest.mock

import pydantic

import flask_typed_routes.openapi as ftr_openapi


def test_get_summary():
    result = ftr_openapi.get_summary("__sample__func__name__")
    assert result == "Sample Func Name"


@unittest.mock.patch("flask_typed_routes.utils.logger")
def test_duplicate_request_field(logger):
    field = unittest.mock.Mock(locator="locator", kind="kind")
    ftr_openapi.duplicate_request_field(field)
    logger.warning.assert_called_once_with('Duplicate request parameter: [name=%s, in=%s]', 'locator', 'kind')


@unittest.mock.patch("flask_typed_routes.utils.logger")
def test_duplicate_request_body(logger):
    ftr_openapi.duplicate_request_body()
    logger.warning.assert_called_once_with("Duplicate request body")


def test_merge_parameters():
    a = ({"name": "1", "in": "query"}, {"name": "1", "in": "query"})
    b = a + ({"name": "2", "in": "query"},)
    expected = (
        {'in': 'query', 'name': '1'},
        {'in': 'query', 'name': '2'},
    )
    result = tuple(ftr_openapi.merge_parameters(a, b))
    assert result == expected


def test_get_parameters():
    class Model(pydantic.BaseModel):
        model_field1: str
        model_field2: str

    schema = {
        "type": "string",
        "title": "Field title",
        "description": "Field description",
        "deprecated": True,
    }
    expected_common = {
        'schema': {'type': 'string'},
        'deprecated': True,
        'description': 'Field description',
    }
    expected = (
        {**expected_common, 'in': 'path', 'name': 'field', 'required': True},
        {**expected_common, 'in': 'query', 'name': 'query_string', 'required': False, 'schema': {'type': 'string'}},
        {**expected_common, 'in': 'query', 'name': 'model_field1', 'required': True, 'schema': {'type': 'string'}},
        {**expected_common, 'in': 'query', 'name': 'model_field2', 'required': False, 'schema': {'type': 'string'}},
    )
    fields = [
        unittest.mock.Mock(locator="field", kind="path", annotation=str),  # required
        unittest.mock.Mock(locator="body", kind="body", annotation=Model),  # ignored
        unittest.mock.Mock(locator="query_string", kind="query", annotation=str),  # optional
        unittest.mock.Mock(locator="query_nested", kind="query", annotation=Model),  # nested
    ]
    model_properties = {
        "field": {**schema},
        "body": {"$ref": "#/components/schemas/Model"},
        "query_string": {**schema},
        "query_nested": {"$ref": "#/components/schemas/Model"},
    }
    model_required_fields = ["field"]
    definitions = {
        "Model": {
            "type": "object",
            "properties": {
                "model_field1": {**schema},
                "model_field2": {**schema},
            },
            "required": ["model_field1"],
        }
    }

    result = ftr_openapi.get_parameters(fields, model_properties, model_required_fields, definitions)
    result = tuple(result)
    assert result == expected


def test_get_unvalidated_parameters():
    result = ftr_openapi.get_unvalidated_parameters(("a", "b"))
    expected = (
        {'in': 'path', 'name': 'a', 'required': True, 'schema': {'type': 'string'}},
        {'in': 'path', 'name': 'b', 'required': True, 'schema': {'type': 'string'}},
    )
    assert tuple(result) == expected


def test_get_request_body_ref():
    class Model(pydantic.BaseModel):
        pass

    fields = [
        unittest.mock.Mock(locator="body", kind="body", annotation=Model)
    ]
    model_properties = {"body": {"$ref": "#/components/schemas/Model"}}
    model_required_fields = ["field"]
    result = ftr_openapi.get_request_body(fields, model_properties, model_required_fields)
    expected = {
        'content': {
            'application/json': {
                'schema': {
                    'properties': {
                        'body': {'$ref': '#/components/schemas/Model'}
                    },
                    'required': [],
                    'type': 'object',
                }
            },
        },
        'required': False,
    }
    assert result == expected


def test_get_request_body_obj():
    fields = [
        unittest.mock.Mock(locator="foo", kind="body", annotation=str),  # required
        unittest.mock.Mock(locator="var", kind="body", annotation=str),  # optional
    ]
    model_properties = {
        "foo": {"type": "string"},
        "var": {"type": "string"},
    }
    model_required_fields = ["foo"]
    result = ftr_openapi.get_request_body(fields, model_properties, model_required_fields)
    expected = {
        'content': {
            'application/json': {
                'schema': {
                    'properties': {
                        'foo': {'type': 'string'},
                        'var': {'type': 'string'},
                    },
                    'required': ['foo'],
                    'type': 'object',
                },
            },
        },
        'required': True,
    }
    assert result == expected
