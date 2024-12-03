import functools
import urllib.parse

import pydantic.version
import pytest


@pytest.fixture(params=["/", "/bp/"])
def url_prefix(request):
    return request.param


pydantic_url = functools.partial(
    urllib.parse.urljoin,
    f"https://errors.pydantic.dev/{pydantic.version.version_short()}/v/"
)


def test_non_typed_view(client, url_prefix):
    url = f"{url_prefix}products/123/"
    expected = {'pk': 123}
    response = client.get(url)
    assert response.json == expected


def test_path(client, url_prefix):
    url = f"{url_prefix}products/path/foo/123/"
    expected = {'category': 'foo', 'product_id': 123}
    response = client.get(url)
    assert response.json == expected


def test_path_bad(client, url_prefix):
    url = f"{url_prefix}products/path/foo/var/"
    response = client.get(url)
    expected = {
        'errors': [
            {
                'input': 'var',
                'loc': ['path', 'product_id'],
                'msg': 'Input should be a valid integer, unable to parse string ' 'as an integer',
                'type': 'int_parsing',
                'url': pydantic_url('int_parsing'),
            }
        ]
    }

    assert response.status_code == 400
    assert response.json == expected


def test_query(client, url_prefix):
    url = f"{url_prefix}products/query/?tag=foo&tag=bar"
    expected = {'limit': 10, 'skip': 0, 'tags': ['foo', 'bar']}
    response = client.get(url)
    assert response.json == expected


def test_query_model(client, url_prefix):
    url = f"{url_prefix}products/query/model/"
    expected = {'extra_field': 'Extra field', 'limit': 10, 'skip': 0, 'sort_by': 'id'}
    response = client.get(url)
    assert response.json == expected


def test_query_bad(client, url_prefix):
    url = f"{url_prefix}products/query/?tag=foo&tag=bar&limit=bad"
    response = client.get(url)
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


def test_header(client, url_prefix):
    url = f"{url_prefix}products/header/"
    expected = {'auth': 'Bearer token', 'tags': ['foo, bar']}
    headers = [
        ("Authorization", "Bearer token"),
        ("X-Tag", "foo"),
        ("X-Tag", "bar"),
    ]
    response = client.get(url, headers=headers)
    assert response.json == expected


def test_header_bad(client, url_prefix):
    url = f"{url_prefix}products/header/"
    headers = [
        ("Authorization", 123),
    ]
    expected = {
        'errors': [
            {
                'ctx': {'pattern': 'Bearer \\w+'},
                'input': '123',
                'loc': ['header', 'Authorization'],
                'msg': "String should match pattern 'Bearer \\w+'",
                'type': 'string_pattern_mismatch',
                'url': pydantic_url('string_pattern_mismatch'),
            }
        ]
    }
    response = client.get(url, headers=headers)
    assert response.status_code == 400
    assert response.json == expected


def test_cookie(client, url_prefix):
    url = f"{url_prefix}products/cookie/"
    expected = {'session_id': '123', 'tags': ['foo, bar']}  # Fixed: The `tags` value is wrong
    client.set_cookie("session-id", "123", path=url)
    client.set_cookie("tag", 'foo, bar', path=url)
    response = client.get(url)
    assert response.json == expected


def test_cookie_bad(client, url_prefix):
    url = f"{url_prefix}products/cookie/"
    expected = {
        'errors': [
            {
                'ctx': {'max_length': 4},
                'input': '12345',
                'loc': ['cookie', 'session-id'],
                'msg': 'String should have at most 4 characters',
                'type': 'string_too_long',
                'url': pydantic_url('string_too_long'),
            }
        ]
    }
    client.set_cookie("session-id", "12345", path=url)
    response = client.get(url)
    assert response.status_code == 400
    assert response.json == expected


def test_body_model(client, url_prefix):
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
    response = client.post(url, json=payload)
    assert response.json == expected


def test_body_model_bad(client, url_prefix):
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
    response = client.post(url, json=payload)
    assert response.status_code == 400
    assert response.json == expected


def test_body_field(client, url_prefix):
    url = f"{url_prefix}products/body/field/"
    payload = {"id": 123, "name": "foo"}
    expected = {'product_id': 123, 'name': 'foo'}
    response = client.post(url, json=payload)
    assert response.json == expected


def test_body_field_bad(client, url_prefix):
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
    response = client.post(url, json=payload)
    assert response.status_code == 400
    assert response.json == expected


def test_body_embed(client, url_prefix):
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
    response = client.post(url, json=payload)
    assert response.json == expected


def test_body_embed_bad(client, url_prefix):
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
    response = client.post(url, json=payload)
    assert response.status_code == 400
    assert response.json == expected


def test_body_forward_refs(client, url_prefix):
    url = f"{url_prefix}products/body/forward-refs/"
    payload = {
        'pk': 123,
        'related': {'pk': 42, 'related': None},
    }
    expected = {
        'pk': 123,
        'related': {'pk': 42, 'related': None},
    }
    response = client.post(url, json=payload)
    assert response.json == expected


def test_func_all_params(client, url_prefix):
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
    }

    headers = {"Authorization": "Bearer token"}
    client.set_cookie("session-id", "123", path=url)
    response = client.post(url, json=payload, headers=headers)
    assert response.json == expected


@pytest.mark.parametrize("url", ["/views/products/foo/", "/method_views/products/foo/"])
def test_view_get(client, url):
    expected = {'category': 'foo', 'limit': 10, 'skip': 0}
    response = client.get(url)
    assert response.json == expected


def test_method_view_post(client):
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
    response = client.post(url, json=payload)
    assert response.json == expected
