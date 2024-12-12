import tests.acceptance

pydantic_url = tests.acceptance.pydantic_url


def test_validate(client_manual):
    url = "/products/validate/123/"
    response = client_manual.get(url)
    expected = {
        'errors': [
            {
                'ctx': {'lt': 100},
                'input': 123,
                'loc': ['path', 'pk'],
                'msg': 'Input should be less than 100',
                'type': 'less_than',
                'url': pydantic_url('less_than'),
            }
        ]
    }
    assert response.status_code == 400
    assert response.json == expected


def test_no_validate(client_manual):
    url = "/products/no-validate/123/"
    response = client_manual.get(url)
    expected = {"product_id": 123}
    assert response.status_code == 200
    assert response.json == expected
