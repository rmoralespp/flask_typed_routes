import flask_typed_routes.errors


def test_handler_returns_correct_response(flask_app_auto):
    error = flask_typed_routes.errors.ValidationError(errors=[{"field": "name", "message": "Invalid"}])
    with flask_app_auto.test_request_context('/'):
        response, status_code = flask_typed_routes.errors.handler(error, 400)

    assert status_code == 400
    assert response.json == {"errors": [{"field": "name", "message": "Invalid"}]}


def test_handler_handles_empty_errors(flask_app_auto):
    error = flask_typed_routes.errors.ValidationError(errors=[])
    with flask_app_auto.test_request_context('/'):
        response, status_code = flask_typed_routes.errors.handler(error, 400)

    assert status_code == 400
    assert response.json == {"errors": []}


def test_handler_handles_multiple_errors(flask_app_auto):
    error = flask_typed_routes.errors.ValidationError(
        errors=[{"field": "name", "message": "Invalid"}, {"field": "age", "message": "Required"}]
    )
    with flask_app_auto.test_request_context('/'):
        response, status_code = flask_typed_routes.errors.handler(error, 400)

    assert status_code == 400
    assert response.json == {
        "errors": [{"field": "name", "message": "Invalid"}, {"field": "age", "message": "Required"}]
    }
