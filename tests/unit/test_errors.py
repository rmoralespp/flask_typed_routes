import flask_typed_routes.errors


def test_handler_returns_correct_response(flask_app):
    error = flask_typed_routes.errors.ValidationError(errors=[{"field": "name", "message": "Invalid"}])
    with flask_app.test_request_context('/'):
        response, status_code = flask_typed_routes.errors.handler(error)

    assert status_code == 400
    assert response.json == {"errors": [{"field": "name", "message": "Invalid"}]}


def test_handler_handles_empty_errors(flask_app):
    error = flask_typed_routes.errors.ValidationError(errors=[])
    with flask_app.test_request_context('/'):
        response, status_code = flask_typed_routes.errors.handler(error)

    assert status_code == 400
    assert response.json == {"errors": []}


def test_handler_handles_multiple_errors(flask_app):
    error = flask_typed_routes.errors.ValidationError(
        errors=[{"field": "name", "message": "Invalid"}, {"field": "age", "message": "Required"}]
    )
    with flask_app.test_request_context('/'):
        response, status_code = flask_typed_routes.errors.handler(error)

    assert status_code == 400
    assert response.json == {
        "errors": [{"field": "name", "message": "Invalid"}, {"field": "age", "message": "Required"}]
    }
