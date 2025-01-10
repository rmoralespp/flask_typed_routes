import collections

import pydantic

import flask_typed_routes.core as ftr_core
import flask_typed_routes.fields as ftr_fields
import flask_typed_routes.openapi as ftr_openapi
import flask_typed_routes.utils as ftr_utils


def test_get_summary():
    result = ftr_openapi.get_summary("sample_func_name")
    assert result == "Sample Func Name"


def test_get_operation_includes_all_fields():
    result = ftr_openapi.get_operation(
        tags=["tag1"],
        summary="Summary",
        description="Description",
        externalDocs={"url": "http://example.com"},
        operationId="operationId",
        parameters=[{"name": "param1"}],
        requestBody={"content": {"application/json": {"schema": {"type": "object"}}}},
        responses={"200": {"description": "Success"}},
        callbacks={"callback1": {"$ref": "#/components/callbacks/Callback"}},
        deprecated=True,
        security=[{"apiKey": []}],
        servers=[{"url": "http://example.com"}],
    )
    expected = {
        "tags": ["tag1"],
        "summary": "Summary",
        "description": "Description",
        "externalDocs": {"url": "http://example.com"},
        "operationId": "operationId",
        "parameters": [{"name": "param1"}],
        "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
        "responses": {"200": {"description": "Success"}},
        "callbacks": {"callback1": {"$ref": "#/components/callbacks/Callback"}},
        "deprecated": True,
        "security": [{"apiKey": []}],
        "servers": [{"url": "http://example.com"}],
    }
    assert result == expected


def test_get_operation_handles_empty_fields():
    result = ftr_openapi.get_operation()
    assert result == dict()


def test_get_openapi_includes_all_fields():
    result = ftr_openapi.get_openapi(
        title="API Title",
        version="1.0.0",
        openapi_version="3.0.0",
        summary="API Summary",
        description="API Description",
        terms_of_service="http://example.com/terms/",
        contact_info={"name": "API Support", "url": "http://example.com/support"},
        license_info={"name": "MIT", "url": "http://example.com/license"},
        servers=[{"url": "http://example.com"}],
        webhooks={"newWebhook": {"post": {"description": "New webhook"}}},
        components={"schemas": {"NewSchema": {"type": "object"}}},
        security=[{"apiKey": []}],
        tags=[{"name": "tag1"}],
        external_docs={"url": "http://example.com/docs"},
    )
    expected = {
        "openapi": "3.0.0",
        "info": {
            "title": "API Title",
            "version": "1.0.0",
            "summary": "API Summary",
            "description": "API Description",
            "termsOfService": "http://example.com/terms/",
            "contact": {"name": "API Support", "url": "http://example.com/support"},
            "license": {"name": "MIT", "url": "http://example.com/license"},
        },
        "paths": collections.defaultdict(dict),
        "components": {'schemas': {'NewSchema': {'type': 'object'}}},
        "servers": [{"url": "http://example.com"}],
        "webhooks": {"newWebhook": {"post": {"description": "New webhook"}}},
        "security": [{"apiKey": []}],
        "tags": [{"name": "tag1"}],
        "externalDocs": {"url": "http://example.com/docs"},
    }
    assert result == expected


def test_get_openapi_handles_empty_fields():
    result = ftr_openapi.get_openapi()
    expected = {
        "openapi": "3.1.0",
        "info": {"title": "API doc", "version": "0.0.0"},
        "paths": collections.defaultdict(dict),
        "components": {
            "schemas": {
                "ValidationError": ftr_openapi.VALIDATION_ERROR_DEF,
                "HTTPValidationError": ftr_openapi.HTTP_VALIDATION_ERROR_DEF,
            },
        },
    }
    assert result == expected


def test_get_operations_includes_all_fields():
    def sample_func():
        """Sample function"""

    field = ftr_core.parse_field("sample_field", str, ftr_fields.Query, None)
    model = pydantic.create_model("SampleModel", sample_field=(str, None))

    setattr(sample_func, ftr_utils.TYPED_ROUTE_REQUEST_MODEL, model)
    setattr(sample_func, ftr_utils.TYPED_ROUTE_PARAM_FIELDS, [field])
    setattr(sample_func, ftr_utils.TYPED_ROUTE_STATUS_CODE, 200)
    setattr(sample_func, ftr_utils.TYPED_ROUTE_OPENAPI, {"summary": "Sample summary"})

    result = ftr_openapi.get_operations(
        sample_func, "/sample", "sample_endpoint", ["GET"], [], 400)
    result = dict(result)
    expected = {
        'components': {'schemas': {}},
        'paths': {
            '/sample': {
                'get': {
                    'description': 'Sample function',
                    'operationId': 'sample_endpoint_get',
                    'parameters': (
                        {
                            'in': 'query',
                            'name': 'sample_field',
                            'required': False,
                            'schema': {'default': None, 'type': 'string'},
                        },
                    ),
                    'responses': {
                        '200': {
                            'content': {
                                'application/json': {'schema': {'type': 'string'}},
                            },
                            'description': 'Success',
                        },
                        '400': {
                            'content': {
                                'application/json': {'schema': {'$ref': '#/components/schemas/HTTPValidationError'}}
                            },
                            'description': 'Validation Error',
                        },
                    },
                    'summary': 'Sample summary',
                }
            }
        },
    }
    assert result == expected


def test_get_operations_handles_empty_fields():
    def sample_func():
        """Sample function"""

    result = ftr_openapi.get_operations(
        sample_func, "/sample", "sample_endpoint", ["GET"], ["field"], 400)
    expected = {
        'components': {'schemas': {}},
        'paths': {
            '/sample': {
                'get': {
                    'summary': 'Sample Endpoint Get',
                    'description': 'Sample function',
                    'operationId': 'sample_endpoint_get',
                    'parameters': (
                        {
                            'in': 'path',
                            'name': 'field',
                            'required': True,
                            'schema': {'type': 'string'},
                        },
                    ),
                    'responses': {
                        'default': {
                            'content': {'application/json': {'schema': {'type': 'string'}}},
                            'description': 'Success',
                        }
                    },
                }
            }
        },
    }

    assert result == expected


def test_get_unvalidated_parameters():
    result = ftr_openapi.get_unvalidated_parameters(["sample_field"])
    expected = [
        {
            'in': 'path',
            'name': 'sample_field',
            'required': True,
            'schema': {'type': 'string'},
        }
    ]
    assert list(result) == expected
