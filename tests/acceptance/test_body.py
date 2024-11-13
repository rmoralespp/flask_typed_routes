def test_create_full_item_by_model(client):
    expected = item = {
        "item_id": "item1",
        "price": 100.0,
        "description": "Item 1 description",
        "country": "ES",
    }
    response = client.post("/items/", json=item)
    assert response.status_code == 201
    assert response.json == expected


def test_create_partial_item_by_model(client):
    item = {
        "item_id": "item2",
        "price": 200.0,
        "country": "ES",
    }
    expected = {**item, "description": None}
    response = client.post("/items/", json=item)
    assert response.status_code == 201
    assert response.json == expected


def test_create_invalid_item_by_model(client):
    item = {
        "item_id": "item3",
        "price": 300.0,
        "country": "ESP",
    }
    expected = {
        'errors': [
            {
                'ctx': {'max_length': 2},
                'input': 'ESP',
                'loc': ['body', 'country'],
                'msg': 'String should have at most 2 characters',
                'type': 'string_too_long',
                'url': 'https://errors.pydantic.dev/2.9/v/string_too_long',
            }
        ]
    }
    response = client.post("/items/", json=item)
    assert response.status_code == 400
    assert response.json == expected


def test_create_user_by_fields(client):
    expected = user = {
        "username": "user1",
        "full_name": "User One",
    }
    response = client.post("/user/", json=user)
    assert response.status_code == 201
    assert response.json == expected


def test_create_bad_user_by_fields(client):
    user = {
        "username": "user2",
        "full_name": 123,
    }
    expected = {
        'errors': [
            {
                'input': 123,
                'loc': ['body', 'full_name'],
                'msg': 'Input should be a valid string',
                'type': 'string_type',
                'url': 'https://errors.pydantic.dev/2.9/v/string_type',
            }
        ]
    }
    response = client.post("/user/", json=user)
    assert response.status_code == 400
    assert response.json == expected
