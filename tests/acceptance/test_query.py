def test_default_params(client):
    expected = {
        'limit': 10,
        'needy': 'value',
        'skip': 0,
        'username': 'my_user',
        'extra': None,
        'tags': [],
    }
    response = client.get("/user/items/my_user/?needy=value")
    assert response.status_code == 200
    assert response.json == expected


def test_passed_params(client):
    expected = {
        'limit': 20,
        'needy': 'value',
        'skip': 10,
        'username': 'my_user',
        'extra': None,
        'tags': [],
    }
    response = client.get("/user/items/my_user/?needy=value&skip=10&limit=20")
    assert response.status_code == 200
    assert response.json == expected


def test_alias_params(client):
    expected = {
        'limit': 10,
        'needy': 'value',
        'skip': 0,
        'username': 'my_user',
        'extra': 'ab',
        'tags': [],
    }
    response = client.get("/user/items/my_user/?needy=value&EXTRA=ab")
    assert response.status_code == 200
    assert response.json == expected


def test_missing_params(client):
    expected = {
        'errors': [
            {
                'input': {'username': 'my_user'},
                'loc': ['query', 'needy'],
                'msg': 'Field required',
                'type': 'missing',
                'url': 'https://errors.pydantic.dev/2.9/v/missing',
            }
        ]
    }
    response = client.get("/user/items/my_user/")
    assert response.status_code == 400
    assert response.json == expected


def test_bad_params(client):
    expected = {
        'errors': [
            {
                'input': 'abc',
                'loc': ['query', 'skip'],
                'msg': 'Input should be a valid integer, unable to parse string as an integer',
                'type': 'int_parsing',
                'url': 'https://errors.pydantic.dev/2.9/v/int_parsing',
            }
        ]
    }
    response = client.get("/user/items/my_user/?needy=value&skip=abc")
    assert response.status_code == 400
    assert response.json == expected


def test_bad_alias_params(client):
    expected = {
        'errors': [
            {
                'ctx': {'max_length': 2},
                'input': 'abc',
                'loc': ['query', 'EXTRA'],
                'msg': 'String should have at most 2 characters',
                'type': 'string_too_long',
                'url': 'https://errors.pydantic.dev/2.9/v/string_too_long',
            }
        ]
    }
    response = client.get("/user/items/my_user/?needy=value&EXTRA=abc")
    assert response.status_code == 400
    assert response.json == expected


def test_model_params(client):
    expected = {
        'limit': 10,
        'offset': 0,
        'order_by': 'created_at',
    }
    response = client.get("/items/?limit=10")
    assert response.json == expected


def test_bad_model_params(client):
    expected = {
        'errors': [
            {
                'ctx': {'gt': 0},
                'input': '0',
                'loc': ['query', 'limit'],
                'msg': 'Input should be greater than 0',
                'type': 'greater_than',
                'url': 'https://errors.pydantic.dev/2.9/v/greater_than',
            }
        ]
    }
    response = client.get("/items/?limit=0")
    assert response.status_code == 400
    assert response.json == expected


def test_multi_params(client):
    expected = {
        'extra': None,
        'limit': 10,
        'needy': 'value',
        'skip': 0,
        'tags': ['tag1', 'tag2'],
        'username': 'my_user',
    }
    response = client.get("/user/items/my_user/?needy=value&tag=tag1&tag=tag2")
    assert response.json == expected


def test_model_params_blueprint(client):
    expected = {
        'limit': 10,
        'offset': 0,
        'order_by': 'created_at',
    }
    response = client.get("/v2/items/?limit=10")
    assert response.json == expected


def test_user_detail_v2(client):
    expected = {'needy': 'value', 'user': 123}
    response = client.get("/v2/users/123/?needy=value")
    assert response.json == expected


def test_user_detail_v1(client):
    expected = {'needy': 'value', 'user': 11}
    response = client.get("/users/11/?needy=value")
    assert response.json == expected
