# -*- coding: utf-8 -*-

import json

import pytest

import tests.utils

pydantic_url = tests.utils.pydantic_url


@pytest.fixture(params=["/", "/bp/"])
def url_prefix(request):
    return request.param


def test_non_typed_view(client_auto, url_prefix):
    url = f"{url_prefix}products/123/"
    expected = {'pk': 123}
    response = client_auto.get(url)
    assert response.json == expected


def test_path(client_auto, url_prefix):
    url = f"{url_prefix}products/path/foo/90/"
    expected = {'category': 'foo', 'product_id': 90}
    response = client_auto.get(url)
    assert response.json == expected


def test_path_bad_less_than(client_auto, url_prefix):
    url = f"{url_prefix}products/path/foo/123/"
    response = client_auto.get(url)
    expected = {
        'errors': [
            {
                'input': '123',
                'loc': ['path', 'product_id'],
                'msg': 'Input should be less than 100',
                'type': 'less_than',
                'url': pydantic_url('less_than'),
            }
        ]
    }

    assert response.status_code == 400
    assert response.json == expected


def test_path_bad_greater_than(client_auto, url_prefix):
    url = f"{url_prefix}products/path/foo/1/"
    response = client_auto.get(url)
    expected = {
        'errors': [
            {
                'input': '1',
                'loc': ['path', 'product_id'],
                'msg': 'Input should be greater than 5',
                'type': 'greater_than',
                'url': pydantic_url('greater_than'),
            }
        ]
    }
    assert response.status_code == 400
    assert response.json == expected


def test_query(client_auto, url_prefix):
    json_data = json.dumps({"a": 1, "b": 2})
    url = f"{url_prefix}products/query/?tag=foo&tag=bar&json_data={json_data}"
    expected = {
        'limit': 10,
        'skip': 0,
        'tags': ['foo', 'bar'],
        "status1": "active",
        "status2": "active",
        "json_data": {"a": 1, "b": 2},
    }
    response = client_auto.get(url)
    assert response.json == expected


def test_query_bad_limit(client_auto, url_prefix):
    url = f"{url_prefix}products/query/?limit=-1"
    expected = {
        'errors': [
            {
                'input': '-1',
                'loc': ['query', 'limit'],
                'msg': 'Input should be greater than or equal to 0',
                'type': 'greater_than_equal',
                'url': pydantic_url('greater_than_equal'),
            }
        ]
    }
    response = client_auto.get(url)
    assert response.json == expected


def test_query_model(client_auto, url_prefix):
    json_data = json.dumps({"a": 1, "b": 2})
    url = f"{url_prefix}products/query/model/?json_data={json_data}"
    expected = {
        'extra_field': 'Extra field',
        'limit': 10,
        'skip': 0,
        'sort_by': 'id',
        'json_data': {'a': 1, 'b': 2},
    }
    response = client_auto.get(url)
    assert response.json == expected


def test_query_bad(client_auto, url_prefix):
    url = f"{url_prefix}products/query/?tag=foo&tag=bar&limit=bad"
    response = client_auto.get(url)
    expected = {
        'errors': [
            {
                'input': 'bad',
                'loc': ['query', 'limit'],
                'msg': 'Input should be a valid integer, unable to parse string ' 'as an integer',
                'type': 'int_parsing',
                'url': pydantic_url('int_parsing'),
            }
        ]
    }

    assert response.status_code == 400
    assert response.json == expected


def test_header(client_auto, url_prefix):
    url = f"{url_prefix}products/header/"
    expected = {'auth': 'Bearer token', 'tags': ['foo', 'bar']}
    headers = [
        ("Authorization", "Bearer token"),
        ("X-Tag", "foo"),
        ("X-Tag", "bar"),
    ]
    response = client_auto.get(url, headers=headers)
    assert response.json == expected


def test_header_bad(client_auto, url_prefix):
    url = f"{url_prefix}products/header/"
    headers = [
        ("Authorization", 123),
    ]
    expected = {
        'errors': [
            {
                'input': '123',
                'loc': ['header', 'Authorization'],
                'msg': "String should match pattern 'Bearer \\w+'",
                'type': 'string_pattern_mismatch',
                'url': pydantic_url('string_pattern_mismatch'),
            }
        ]
    }
    response = client_auto.get(url, headers=headers)
    assert response.status_code == 400
    assert response.json == expected


def test_cookie(client_auto, url_prefix):
    url = f"{url_prefix}products/cookie/"
    expected = {'session_id': '123', 'tags': ['foo, bar']}  # Fixed: The `tags` value is wrong
    client_auto.set_cookie("session-id", "123", path=url)
    client_auto.set_cookie("tag", 'foo, bar', path=url)
    response = client_auto.get(url)
    assert response.json == expected


def test_cookie_bad(client_auto, url_prefix):
    url = f"{url_prefix}products/cookie/"
    expected = {
        'errors': [
            {
                'input': '12345',
                'loc': ['cookie', 'session-id'],
                'msg': 'String should have at most 4 characters',
                'type': 'string_too_long',
                'url': pydantic_url('string_too_long'),
            }
        ]
    }
    client_auto.set_cookie("session-id", "12345", path=url)
    response = client_auto.get(url)
    assert response.status_code == 400
    assert response.json == expected


def test_body_model(client_auto, url_prefix):
    url = f"{url_prefix}products/body/model/"
    payload = {"id": 123, "name": "foo", "price": 1.23, "stock": 42, "category": "bar"}
    expected = {
        'product_id': 123,
        'name': 'foo',
        'price': 1.23,
        'stock': 42,
        'category': 'bar',
        'description': None,
    }
    response = client_auto.post(url, json=payload)
    assert response.json == expected


def test_body_model_bad(client_auto, url_prefix):
    url = f"{url_prefix}products/body/model/"
    payload = {"id": 123, "name": "foo", "price": "fob", "stock": 42, "category": 42}
    expected = {
        'errors': [
            {
                'input': 'fob',
                'loc': ['body', 'price'],
                'msg': 'Input should be a valid number, unable to parse string as ' 'a number',
                'type': 'float_parsing',
                'url': pydantic_url('float_parsing'),
            },
            {
                'input': 42,
                'loc': ['body', 'category'],
                'msg': 'Input should be a valid string',
                'type': 'string_type',
                'url': pydantic_url('string_type'),
            },
        ]
    }
    response = client_auto.post(url, json=payload)
    assert response.status_code == 400
    assert response.json == expected


def test_body_field(client_auto, url_prefix):
    url = f"{url_prefix}products/body/field/"
    payload = {"id": 123, "name": "foo"}
    expected = {'product_id': 123, 'name': 'foo'}
    response = client_auto.post(url, json=payload)
    assert response.json == expected


def test_body_field_bad(client_auto, url_prefix):
    url = f"{url_prefix}products/body/field/"
    payload = {"id": "fob", "name": 42}
    expected = {
        'errors': [
            {
                'input': 'fob',
                'loc': ['body', 'id'],
                'msg': 'Input should be a valid integer, unable to parse string as ' 'an integer',
                'type': 'int_parsing',
                'url': pydantic_url('int_parsing'),
            },
            {
                'input': 42,
                'loc': ['body', 'name'],
                'msg': 'Input should be a valid string',
                'type': 'string_type',
                'url': pydantic_url('string_type'),
            },
        ]
    }
    response = client_auto.post(url, json=payload)
    assert response.status_code == 400
    assert response.json == expected


def test_body_embed(client_auto, url_prefix):
    url = f"{url_prefix}products/body/embed/"
    payload = {
        'product': {"id": 123, "name": "foo", "price": 1.23, "stock": 42, "category": "bar"},
        'user': {"id": 42, "username": "baz", "password": "12345"},
    }
    expected = {
        'product': {
            'category': 'bar',
            'description': None,
            'name': 'foo',
            'price': 1.23,
            'product_id': 123,
            'stock': 42,
        },
        'user': {
            'full_name': None,
            'password': '12345',
            'user_id': 42,
            'username': 'baz',
        },
    }
    response = client_auto.post(url, json=payload)
    assert response.json == expected


def test_body_embed_bad(client_auto, url_prefix):
    url = f"{url_prefix}products/body/embed/"
    payload = {
        'product': {"id": 123, "name": "foo", "price": "fob", "stock": 42, "category": 42},
        'user': {"id": "baz", "username": 42, "password": 12345},
    }
    expected = {
        'errors': [
            {
                'input': 'fob',
                'loc': ['body', 'product', 'price'],
                'msg': 'Input should be a valid number, unable to parse string as ' 'a number',
                'type': 'float_parsing',
                'url': pydantic_url('float_parsing'),
            },
            {
                'input': 42,
                'loc': ['body', 'product', 'category'],
                'msg': 'Input should be a valid string',
                'type': 'string_type',
                'url': pydantic_url('string_type'),
            },
            {
                'input': 'baz',
                'loc': ['body', 'user', 'id'],
                'msg': 'Input should be a valid integer, unable to parse string ' 'as an integer',
                'type': 'int_parsing',
                'url': pydantic_url('int_parsing'),
            },
            {
                'input': 42,
                'loc': ['body', 'user', 'username'],
                'msg': 'Input should be a valid string',
                'type': 'string_type',
                'url': pydantic_url('string_type'),
            },
            {
                'input': 12345,
                'loc': ['body', 'user', 'password'],
                'msg': 'Input should be a valid string',
                'type': 'string_type',
                'url': pydantic_url('string_type'),
            },
        ]
    }
    response = client_auto.post(url, json=payload)
    assert response.status_code == 400
    assert response.json == expected


def test_body_forward_refs(client_auto, url_prefix):
    url = f"{url_prefix}products/body/forward-refs/"
    payload = {
        'pk': 123,
        'related': {'pk': 42, 'related': None},
    }
    expected = {
        'pk': 123,
        'related': {'pk': 42, 'related': None},
    }
    response = client_auto.post(url, json=payload)
    assert response.json == expected


def test_test_depends(client_auto, url_prefix):
    url = f"{url_prefix}products/depends/"
    expected = {'dependency': 'ok'}
    response = client_auto.get(url)
    assert response.json == expected


def test_test_depends_fail(client_auto, url_prefix):
    url = f"{url_prefix}products/depends/fail/"
    response = client_auto.get(url)
    assert response.status_code == 400


def test_test_non_returning_depends(client_auto, url_prefix):
    url = f"{url_prefix}products/non-returning-depends/"
    response = client_auto.get(url)
    assert response.json == dict()


def test_test_non_returning_fail(client_auto, url_prefix):
    url = f"{url_prefix}products/non-returning-depends/fail/"
    response = client_auto.get(url)
    assert response.status_code == 400


def test_func_all_params(client_auto, url_prefix):
    url = f"{url_prefix}products/all/foo/123/"
    payload = {
        'id': 123,
        'name': 'foo',
        'price': 1.23,
        'stock': 42,
    }
    expected = {
        'auth': 'Bearer token',
        'category': 'foo',
        'limit': 10,
        'product': {
            'category': None,
            'description': None,
            'name': 'foo',
            'price': 1.23,
            'product_id': 123,
            'stock': 42,
        },
        'product_id': 123,
        'session_id': '123',
        'skip': 0,
        'my_dependency': 'ok',
    }

    headers = {"Authorization": "Bearer token"}
    client_auto.set_cookie("session-id", "123", path=url)
    response = client_auto.post(url, json=payload, headers=headers)
    assert response.json == expected


@pytest.mark.parametrize("url", ["/views/products/foo/", "/method_views/products/foo/"])
def test_view_get(client_auto, url):
    expected = {'category': 'foo', 'limit': 10, 'skip': 0}
    response = client_auto.get(url)
    assert response.json == expected


def test_method_view_post(client_auto):
    url = "/method_views/products/foo/"
    payload = {
        'id': 123,
        'name': 'foo',
        'price': 1.23,
        'stock': 42,
    }
    expected = {
        'category': 'foo',
        'product': {
            'category': None,
            'description': None,
            'name': 'foo',
            'price': 1.23,
            'product_id': 123,
            'stock': 42,
        },
    }
    response = client_auto.post(url, json=payload)
    assert response.json == expected


def test_func_mixed_annotations(client_auto, url_prefix):
    url = f"{url_prefix}products/mixed/?cat=1234567890"
    expected = {"category": "1234567890"}
    response = client_auto.get(url)
    assert response.json == expected


def test_func_mixed_annotations_bad_min_len(client_auto, url_prefix):
    url = f"{url_prefix}products/mixed/?cat=12345678"
    response = client_auto.get(url)
    expected = {
        'errors': [
            {
                'input': '12345678',
                'loc': ['query', 'cat'],
                'msg': 'String should have at least 9 characters',
                'type': 'string_too_short',
                'url': pydantic_url('string_too_short'),
            }
        ]
    }

    assert response.status_code == 400
    assert response.json == expected


def test_func_mixed_annotations_bad_max_len(client_auto, url_prefix):
    url = f"{url_prefix}products/mixed/?cat=123456789012"
    response = client_auto.get(url)
    expected = {
        'errors': [
            {
                'input': '123456789012',
                'loc': ['query', 'cat'],
                'msg': 'String should have at most 11 characters',
                'type': 'string_too_long',
                'url': pydantic_url('string_too_long'),
            }
        ]
    }

    assert response.status_code == 400
    assert response.json == expected


def test_func_mixed_annotations_bad_pattern(client_auto, url_prefix):
    url = f"{url_prefix}products/mixed/?cat=aaaaaaaaaa"
    response = client_auto.get(url)
    expected = {
        'errors': [
            {
                'input': 'aaaaaaaaaa',
                'loc': ['query', 'cat'],
                'msg': "String should match pattern '\\d{10}'",
                'type': 'string_pattern_mismatch',
                'url': pydantic_url('string_pattern_mismatch'),
            }
        ]
    }

    assert response.status_code == 400
    assert response.json == expected
