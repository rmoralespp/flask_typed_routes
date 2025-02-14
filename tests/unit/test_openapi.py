import unittest.mock

import pydantic

import flask_typed_routes.openapi as ftr_openapi
import flask_typed_routes.utils as ftr_utils


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
    a = ({"name": "1", "in": "query"}, {"name": "1", "in": "query"}, {"$ref": "#/foo"})
    b = a + ({"name": "2", "in": "query"}, {"$ref": "#/foo"}, {"$ref": "#/var"})
    expected = (
        {'in': 'query', 'name': '1'},
        {'$ref': '#/foo'},
        {'in': 'query', 'name': '2'},
        {'$ref': '#/var'},
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
        'style': 'foo',
        'explode': 'explode',
    }
    expected = (
        {**expected_common, 'in': 'path', 'name': 'field', 'required': True},
        {**expected_common, 'in': 'query', 'name': 'query_string', 'required': False, 'schema': {'type': 'string'}},
        {**expected_common, 'in': 'query', 'name': 'model_field1', 'required': True, 'schema': {'type': 'string'}},
        {**expected_common, 'in': 'query', 'name': 'model_field2', 'required': False, 'schema': {'type': 'string'}},
    )
    fields = [
        unittest.mock.Mock(locator="field", kind="path", annotation=str, explode='explode', style='foo'),
        unittest.mock.Mock(locator="body", kind="body", annotation=Model, explode='explode', style='foo'),
        unittest.mock.Mock(locator="query_string", kind="query", annotation=str, explode='explode', style='foo'),
        unittest.mock.Mock(locator="query_nested", kind="query", annotation=Model, explode='explode', style='foo'),
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


def test_get_json_parameters():
    fields = [
        unittest.mock.Mock(locator="field", kind="query", annotation=dict),
    ]
    model_properties = {
        "field": {
            "contentMediaType": "application/json",
            "contentSchema": {"type": "object"},
        },
    }
    expected = (
        {
            'content': {'application/json': {'schema': {'type': 'object'}}},
            'in': 'query',
            'name': 'field',
            'required': False,
        },
    )
    result = ftr_openapi.get_parameters(fields, model_properties, (), {})
    assert tuple(result) == expected


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

    fields = [unittest.mock.Mock(locator="body", kind="body", annotation=Model)]
    model_properties = {"body": {"$ref": "#/components/schemas/Model"}}
    model_required_fields = ["field"]
    result = ftr_openapi.get_request_body(fields, model_properties, model_required_fields)
    expected = {
        'content': {
            'application/json': {
                'schema': {
                    'properties': {'body': {'$ref': '#/components/schemas/Model'}},
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


def test_get_request_body_no_fields():
    result = ftr_openapi.get_request_body([], {}, [])
    assert result is None


def test_openapi_init_default():
    expected = {
        'components': None,
        'contact_info': None,
        'description': None,
        'external_docs': None,
        'license_info': None,
        'openapi_version': '3.1.0',
        'paths': {},
        'servers': None,
        'summary': None,
        'tags': None,
        'terms_of_service': None,
        'title': 'API doc',
        'version': '0.0.1',
        'webhooks': None,
    }
    assert ftr_openapi.OpenApi().__dict__ == expected


def test_openapi_init_filled():
    params = {
        'components': object(),
        'contact_info': object(),
        'description': object(),
        'external_docs': object(),
        'license_info': object(),
        'openapi_version': '3.1.0',
        'servers': object(),
        'summary': object(),
        'tags': object(),
        'terms_of_service': object(),
        'title': object(),
        'version': object(),
        'webhooks': object(),
    }
    expected = {**params, 'paths': {}}
    assert ftr_openapi.OpenApi(**params).__dict__ == expected


def test_openapi_models_json_schema():
    class Model1(pydantic.BaseModel):
        field1: str
        field2: str

    class Model2(pydantic.BaseModel):
        field3: str
        field4: str
        embed: list[Model1]

    result = ftr_openapi.OpenApi.models_json_schema([Model1, Model2])
    expected = (
        {
            (Model1, 'validation'): {'$ref': '#/components/schemas/Model1'},
            (Model2, 'validation'): {'$ref': '#/components/schemas/Model2'},
        },
        {
            '$defs': {
                'Model1': {
                    'properties': {
                        'field1': {'title': 'Field1', 'type': 'string'},
                        'field2': {'title': 'Field2', 'type': 'string'},
                    },
                    'required': ['field1', 'field2'],
                    'title': 'Model1',
                    'type': 'object',
                },
                'Model2': {
                    'properties': {
                        'embed': {'items': {'$ref': '#/components/schemas/Model1'}, 'title': 'Embed', 'type': 'array'},
                        'field3': {'title': 'Field3', 'type': 'string'},
                        'field4': {'title': 'Field4', 'type': 'string'},
                    },
                    'required': ['field3', 'field4', 'embed'],
                    'title': 'Model2',
                    'type': 'object',
                },
            }
        },
    )

    assert result == expected


def test_openapi_routes_json_schema():
    def my_func1(arg1: str):
        pass

    def my_func2(arg1: str):
        pass

    class Model(pydantic.BaseModel):
        field: str

    setattr(my_func1, ftr_utils.ROUTE_REQUEST_MODEL, Model)
    routes = [
        ftr_utils.RouteInfo(my_func1, "/path1", ("arg1",), "my_func1", ("GET",)),
        ftr_utils.RouteInfo(my_func2, "/path2", ("arg1",), "my_func2", ("POST",)),
    ]

    expected = (
        {(Model, 'validation'): {'$ref': '#/components/schemas/Model'}},
        {
            'HTTPValidationError': ftr_openapi.HTTP_VALIDATION_ERROR_DEF,
            'Model': {
                'properties': {'field': {'title': 'Field', 'type': 'string'}},
                'required': ['field'],
                'title': 'Model',
                'type': 'object',
            },
            'ValidationError': ftr_openapi.VALIDATION_ERROR_DEF,
        },
        [
            (
                routes[0],
                Model,
            ),
            (routes[1], None),
        ],
    )
    result = ftr_openapi.OpenApi.routes_json_schema(routes)
    assert result == expected


def test_get_schema_empty_routes():
    result = ftr_openapi.OpenApi().get_schema([], 422)
    expected = {
        'components': {},
        'info': {'title': 'API doc', 'version': '0.0.1'},
        'openapi': '3.1.0',
        'paths': {},
    }
    assert result == expected


def test_get_schema():
    def my_func1():
        pass

    def my_func2(arg1: str):
        pass

    class Model(pydantic.BaseModel):
        field: int

    setattr(my_func1, ftr_utils.ROUTE_REQUEST_MODEL, Model)
    setattr(my_func1, ftr_utils.ROUTE_PARAM_FIELDS, [
        unittest.mock.Mock(locator="field", kind="query", annotation=int, explode='explode', style='style')])
    routes = [
        ftr_utils.RouteInfo(my_func1, "/path1", ("arg1",), "my_func1", ("GET",)),
        ftr_utils.RouteInfo(my_func2, "/path2", ("arg1",), "my_func2", ("POST",)),
    ]
    expected = {
        'components': {
            'schemas': {
                'HTTPValidationError': ftr_openapi.HTTP_VALIDATION_ERROR_DEF,
                'ValidationError': ftr_openapi.VALIDATION_ERROR_DEF,
            }
        },
        'info': {'title': 'API doc', 'version': '0.0.1'},
        'openapi': '3.1.0',
        'paths': {
            '/path1': {
                'get': {
                    'description': '',
                    'operationId': 'my_func1_get',
                    'parameters': (
                        {
                            'in': 'query',
                            'name': 'field',
                            'required': True,
                            'schema': {'type': 'integer'},
                            'style': 'style',
                            'explode': 'explode',
                        },
                    ),
                    'responses': {
                        'default': {
                            'content': {'application/json': {'schema': {'type': 'string'}}},
                            'description': 'Success',
                        },
                        '422': {
                            'content': {
                                'application/json': {'schema': {'$ref': '#/components/schemas/HTTPValidationError'}}
                            },
                            'description': 'Validation Error',
                        },
                    },
                    'summary': 'My Func1 Get',
                }
            },
            '/path2': {
                'post': {
                    'description': '',
                    'operationId': 'my_func2_post',
                    'parameters': (
                        {'in': 'path', 'name': 'arg1', 'required': True, 'schema': {'type': 'string'}},
                    ),
                    'responses': {
                        'default': {
                            'content': {'application/json': {'schema': {'type': 'string'}}},
                            'description': 'Success',
                        }
                    },
                    'summary': 'My Func2 Post',
                }
            },
        },
    }
    result = ftr_openapi.OpenApi().get_schema(routes, 422)
    assert result == expected


def test_register_route():
    ini_paths = {"/path1": {"get": 'var'}, "/path2": {}}
    new_paths = {"/path1": {"post": 'foo'}, "/path2": {"get": 'foo'}}
    route = unittest.mock.Mock()
    error_status_code = unittest.mock.Mock()
    model_schema = unittest.mock.Mock()
    definitions = unittest.mock.Mock()
    openapi = ftr_openapi.OpenApi()
    openapi.get_route_operations = unittest.mock.Mock(return_value=new_paths)
    openapi.paths = ini_paths
    openapi.register_route(route, error_status_code, model_schema, definitions)
    expected = {'/path1': {'get': 'var', 'post': 'foo'}, '/path2': {'get': 'foo'}}
    assert openapi.paths == expected
    openapi.get_route_operations.assert_called_once_with(route, error_status_code, model_schema, definitions)
