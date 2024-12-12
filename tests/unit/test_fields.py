import unittest.mock as mock

import flask
import pytest
import werkzeug.test
import werkzeug.wrappers

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields


def test_path_field(flask_app):
    with flask_app.test_request_context('/'):
        flask.request.view_args = {'id': 123}
        assert ftr_fields.Path(alias='id').value == 123


@pytest.mark.parametrize('multi', [True, False])
def test_query_field(flask_app, multi):
    expected = ['term'] if multi else 'term'
    with flask_app.test_request_context('/?search=term'):
        result = ftr_fields.Query(alias='search', multi=multi).value
        assert result == expected


@pytest.mark.parametrize('multi', [True, False])
def test_cookie_field(flask_app, multi):
    expected = ['abc123', 'abc124'] if multi else 'abc123'
    with flask_app.test_request_context('/'):
        headers = [('Cookie', 'session_id=abc123; session_id=abc124')]
        builder = werkzeug.test.EnvironBuilder(path='/', headers=headers)
        env = builder.get_environ()
        request = werkzeug.wrappers.Request(env)
        with mock.patch('flask.request', request):
            result = ftr_fields.Cookie(alias='session_id', multi=multi).value

        assert result == expected


def test_header_field(flask_app):
    expected = 'Bearer token1'
    headers = [
        ('Authorization', 'Bearer token1'),
    ]
    # Fixed: The `headers` multi dont work
    with flask_app.test_request_context('/', headers=headers):
        result = ftr_fields.Header(alias='Authorization').value
        assert result == expected


def test_body_field(flask_app):
    with flask_app.test_request_context('/', json={'key': 'value'}):
        result = ftr_fields.Body().value
    assert result == {'key': 'value'}


def test_body_embed_field(flask_app):
    with flask_app.test_request_context('/', json={'key': {"subkey": "value"}}):
        result = ftr_fields.Body(alias="key", embed=True).value
    assert result == {"subkey": "value"}


@pytest.mark.parametrize('field_class', [ftr_fields.Path, ftr_fields.Query, ftr_fields.Cookie])
def test_bad_embed_field(field_class):
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        field_class(embed=True)


@pytest.mark.parametrize('field_class', [ftr_fields.Body, ftr_fields.Path])
def test_bad_multi_field(field_class):
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        field_class(multi=True)
