import typing
import unittest.mock as mock

import flask
import pydantic
import pytest
import werkzeug.test
import werkzeug.wrappers

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields


class MyListFieldModel(pydantic.BaseModel):
    list_field: typing.Annotated[list[str], pydantic.Field(alias='list-field')]


def test_path_field(flask_app_auto):
    with flask_app_auto.test_request_context('/'):
        flask.request.view_args = {'id': 123}
        assert ftr_fields.Path(alias='id').value == 123


@pytest.mark.parametrize(
    'url, annotation, expected',
    [
        ('/?search=term1&search=term2', list[str], ['term1', 'term2']),
        ('/?search=term1&search=term2', str, 'term1'),
        ('/?search=term1,term2', list[str], ['term1,term2']),
        ('/?search=term1,term2', str, 'term1,term2'),
    ]
)
def test_query_standalone_field(flask_app_auto, url, annotation, expected):
    with flask_app_auto.test_request_context(url):
        field = ftr_fields.Query(alias='search')
        field.annotation = annotation
        assert field.value == expected


@pytest.mark.parametrize('url, expected', [
    ('/?list-field=term1&list-field=term2', {'list-field': ['term1', 'term2']}),
    ('/?list-field=term1,term2', {'list-field': ['term1,term2']}),
])
def test_query_model_list_field(flask_app_auto, url, expected):
    with flask_app_auto.test_request_context(url):
        field = ftr_fields.Query()
        field.annotation = MyListFieldModel
        assert field.value == expected


@pytest.mark.parametrize(
    'cookie, annotation, expected',
    [
        ('session_id=abc123; session_id=abc124', list[str], ['abc123', 'abc124']),
        ('session_id=abc123; session_id=abc124', str, 'abc123'),
        ('session_id=abc123', list[str], ['abc123']),
        ('session_id=abc123', str, 'abc123'),
    ]
)
def test_cookie_standalone_field(flask_app_auto, cookie, annotation, expected):
    with flask_app_auto.test_request_context('/'):
        headers = [('Cookie', cookie)]
        builder = werkzeug.test.EnvironBuilder(path='/', headers=headers)
        env = builder.get_environ()
        request = werkzeug.wrappers.Request(env)
        with mock.patch('flask.request', request):
            field = ftr_fields.Cookie(alias='session_id')
            field.annotation = annotation
            assert field.value == expected


@pytest.mark.parametrize('cookie, expected', [
    ('list-field=abc123; list-field=abc124', {'list-field': ['abc123', 'abc124']}),
    ('list-field=abc123,abc124', {'list-field': ['abc123,abc124']}),
])
def test_cookie_model_list_field(flask_app_auto, cookie, expected):
    with flask_app_auto.test_request_context('/'):
        headers = [('Cookie', cookie)]
        builder = werkzeug.test.EnvironBuilder(path='/', headers=headers)
        env = builder.get_environ()
        request = werkzeug.wrappers.Request(env)
        with mock.patch('flask.request', request):
            field = ftr_fields.Cookie()
            field.annotation = MyListFieldModel
            assert field.value == expected


def test_header_standalone_field(flask_app_auto):
    expected = 'Bearer token1'
    headers = [
        ('Authorization', 'Bearer token1'),
    ]
    with flask_app_auto.test_request_context('/', headers=headers):
        result = ftr_fields.Header(alias='Authorization').value
        assert result == expected


def test_body_field(flask_app_auto):
    with flask_app_auto.test_request_context('/', json={'key': 'value'}):
        result = ftr_fields.Body().value
    assert result == {'key': 'value'}


def test_body_embed_field(flask_app_auto):
    with flask_app_auto.test_request_context('/', json={'key': {"subkey": "value"}}):
        result = ftr_fields.Body(alias="key", embed=True).value
    assert result == {"subkey": "value"}


@pytest.mark.parametrize('field_class', [ftr_fields.Path, ftr_fields.Query, ftr_fields.Cookie])
def test_bad_embed_field(field_class):
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        field_class(embed=True)


@pytest.mark.parametrize('annotation, expected', [
    (str, False),
    (list, True),
    (list[str], True),
    (typing.List[str], True), # noqa UP006
    (set, True),
    (set[str], True),
    (typing.Set[str], True), # noqa UP006
    (frozenset, True),
    (frozenset[str], True),
    (typing.FrozenSet[str], True), # noqa UP006
    (tuple, True),
    (tuple[str], True),
    (typing.Tuple[str], True), # noqa UP006
    (typing.Annotated[str, pydantic.Field(alias='field')], False),
    (typing.Annotated[list[str], pydantic.Field(alias='list-field')], True),
    (typing.Annotated[typing.List[str], pydantic.Field(alias='list-field')], True), # noqa UP006
])
def test_field_is_multi_field(annotation, expected):
    assert ftr_fields.Field.is_multi_field(annotation) == expected
