import pytest


@pytest.fixture(params=["/", "/bp/"])
def url_prefix(request):
    return request.param


def test_path(client, url_prefix):
    url = f"{url_prefix}products/path/foo/123/"
    expected = {'category': 'foo', 'product_id': 123}
    response = client.get(url)
    assert response.json == expected


def test_query(client, url_prefix):
    url = f"{url_prefix}products/query/?tag=foo&tag=bar"
    expected = {'limit': 10, 'skip': 0, 'tags': ['foo', 'bar']}
    response = client.get(url)
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


def test_cookie(client, url_prefix):
    url = f"{url_prefix}products/cookie/"
    expected = {'session_id': '123', 'tags': ['foo, bar']}  # Fixed: The `tags` value is wrong
    client.set_cookie("session-id", "123", path=url)
    client.set_cookie("tag", 'foo, bar', path=url)
    response = client.get(url)
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


def test_body_field(client, url_prefix):
    url = f"{url_prefix}products/body/field/"
    payload = {"id": 123, "name": "foo"}
    expected = {'product_id': 123, 'name': 'foo'}
    response = client.post(url, json=payload)
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
