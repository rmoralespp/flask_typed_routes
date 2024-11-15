def test_valid_param(client):
    response = client.get("/items/42/")
    assert response.status_code == 200
    assert response.json == {"item_id": 42}


def test_bad_param(client):
    expected = {
        'errors': [
            {
                'input': 'abc',
                'loc': ['path', 'item_id'],
                'msg': 'Input should be a valid integer, unable to parse string as an integer',
                'type': 'int_parsing',
                'url': 'https://errors.pydantic.dev/2.9/v/int_parsing',
            }
        ]
    }
    response = client.get("/items/abc/")
    assert response.status_code == 400
    assert response.json == expected


def test_valid_param_non_annotation(client):
    response = client.get("/items/42/details/")
    assert response.status_code == 200
    assert response.json == {"item_id": '42'}

