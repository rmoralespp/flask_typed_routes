import typing
import unittest.mock as mock

import flask
import pydantic
import pytest
import werkzeug.test
import werkzeug.wrappers

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.fields as ftr_fields


@pytest.mark.parametrize(
    'view_args, annotation, explode, expected',
    [
        ({}, str, True, ftr_fields.Unset),
        ({}, str, False, ftr_fields.Unset),
        ({'id': ''}, str, True, ''),
        ({'id': ''}, str, False, ''),
        ({'id': '5'}, str, True, '5'),
        ({'id': '5'}, str, False, '5'),
        ({'id': '5'}, list[str], True, ['5']),
        ({'id': '5'}, list[str], False, ['5']),
        ({'id': '3,4,5'}, list[str], True, ['3', '4', '5']),
        ({'id': ' 3 , 4 , 5 '}, list[str], True, ['3', '4', '5']),  # with spaces
        ({'id': '3,4,5'}, list[str], False, ['3', '4', '5']),
        ({'id': 'a,1,b,2'}, dict, False, {'a': '1', 'b': '2'}),
        ({'id': ' a , 1 , b , 2 '}, dict, False, {'a': '1', 'b': '2'}),  # with spaces
        ({'id': 'a,1,b,2,c'}, dict, False, {'a': '1', 'b': '2', 'c': ''}),  # odd number of elements
        ({'id': 'a,1,a,2'}, dict, False, {'a': '2'}),  # duplicate keys
        ({'id': 'a,'}, dict, False, {'a': ''}),
        ({'id': 'a'}, dict, False, {'a': ''}),
        ({'id': 'a=1,b=2'}, pydantic.create_model("Model"), True, {'a': '1', 'b': '2'}),
        ({'id': 'a=1,b=2'}, dict, True, {'a': '1', 'b': '2'}),
        ({'id': 'a=1,a=2'}, dict, True, {'a': '2'}),  # duplicate keys
        ({'id': ' a = 1 , b = 2 '}, dict, True, {'a': '1', 'b': '2'}),  # with spaces
        ({'id': 'a='}, dict, True, {'a': ''}),  # incomplete pair
        ({'id': 'a==b'}, dict, True, {'a': '=b'}),
        ({'id': '='}, dict, True, {}),  # incomplete pair
        ({'id': '=='}, dict, True, {"=": ""}),  # bad pair
    ]
)
@pytest.mark.parametrize('style', [None, 'simple'])
def test_path_field(flask_app_auto, style, view_args, annotation, explode, expected):
    with flask_app_auto.test_request_context('/'):
        flask.request.view_args = view_args
        obj = ftr_fields.Path(alias='id', explode=explode, style=style)
        obj.annotation = annotation
        assert obj.value == expected


@pytest.mark.parametrize('style', ['form', 'spaceDelimited', 'pipeDelimited'])
def test_path_field_bad_style(style):
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        ftr_fields.Path(style=style)


@pytest.mark.parametrize(
    'url, annotation, style, expected',
    [
        ('/?search=term1&search=term2', list[str], 'form', ['term1', 'term2']),
        ('/?search=term1&search=term2', list[str], 'spaceDelimited', ['term1', 'term2']),
        ('/?search=term1&search=term2', list[str], 'pipeDelimited', ['term1', 'term2']),
        ('/?search=term1&search=term2', list[str], None, ['term1', 'term2']),
        ('/?search=term1,term2', list[str], None, ['term1,term2']),
        ('/?search=', list[str], None, ['']),
        ('/', list[str], None, ftr_fields.Unset),
        ('/?search=term1&search=term2', str, 'form', 'term1'),
        ('/?search=term1&search=term2', str, 'spaceDelimited', 'term1'),
        ('/?search=term1&search=term2', str, 'pipeDelimited', 'term1'),
        ('/?search=term1&search=term2', str, None, 'term1'),
        ('/?search=term1,term2', str, None, 'term1,term2'),
        ('/?search=', str, None, ''),
        ('/', str, None, ftr_fields.Unset),
        ('/?search=role,admin,name,Alex', dict, None, dict()),  # because if exploded
    ]
)
@pytest.mark.parametrize('standalone', [True, False])
def test_query_field_explode(flask_app_auto, standalone, url, annotation, style, expected):
    with flask_app_auto.test_request_context(url):
        field = ftr_fields.Query(alias='search', explode=True, style=style)
        if standalone:
            field.annotation = annotation
            assert field.value == expected
        else:
            field.annotation = pydantic.create_model('QueryModel', search=(annotation, ...))
            if expected == ftr_fields.Unset:
                assert field.value == dict()
            else:
                assert field.value == {'search': expected}


@pytest.mark.parametrize(
    'url, annotation, style, expected',
    [
        ('/?search=term1&search=term2', list[str], 'form', ['term1']),
        ('/?search=term1&search=term2', list[str], 'spaceDelimited', ['term1']),
        ('/?search=term1&search=term2', list[str], 'pipeDelimited', ['term1']),
        ('/?search=term1&search=term2', list[str], None, ['term1']),
        ('/?search=term1,term2', list[str], None, ['term1', 'term2']),
        ('/?search=term1|term2', list[str], "pipeDelimited", ['term1', 'term2']),
        ('/?search=term1 term2', list[str], "spaceDelimited", ['term1', 'term2']),
        ('/?search=', list[str], None, []),
        ('/', list[str], None, ftr_fields.Unset),
        ('/?search=term1&search=term2', str, 'form', 'term1'),
        ('/?search=term1&search=term2', str, 'spaceDelimited', 'term1'),
        ('/?search=term1&search=term2', str, 'pipeDelimited', 'term1'),
        ('/?search=term1&search=term2', str, None, 'term1'),
        ('/?search=term1,term2', str, None, 'term1,term2'),
        ('/?search=role,admin', dict, None, {'role': 'admin'}),
        ('/?search=term1|term2', str, "pipeDelimited", 'term1|term2'),
        ('/?search=term1 term2', str, "spaceDelimited", 'term1 term2'),
        ('/?search=', str, None, ''),
        ('/', str, None, ftr_fields.Unset),
        ('/?search=role,admin,name,Alex', dict, None, {'role': 'admin', 'name': 'Alex'}),  # multiple pairs
        ('/?search=role,admin,role,user', dict, None, {'role': 'user'}),  # duplicate keys
        ('/?search=role,admin,name', dict, None, {'role': 'admin', 'name': ''}),  # odd number of elements
        ('/?search=term1|term2', dict, "pipeDelimited", dict()),   # because if style is pipeDelimited
        ('/?search=term1 term2', dict, "spaceDelimited", dict()),  # because if style is spaceDelimited
    ]
)
@pytest.mark.parametrize('standalone', [True, False])
def test_query_field_non_explode(flask_app_auto, standalone, url, annotation, style, expected):
    with flask_app_auto.test_request_context(url):
        field = ftr_fields.Query(alias='search', explode=False, style=style)
        if standalone:
            field.annotation = annotation
            assert field.value == expected
        else:
            field.annotation = pydantic.create_model('QueryModel', search=(annotation, ...))
            if expected == ftr_fields.Unset:
                assert field.value == dict()
            else:
                assert field.value == {'search': expected}


def test_query_field_bad_style():
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        ftr_fields.Query(style='simple')


@pytest.mark.parametrize(
    'cookie, annotation, explode, expected',
    [
        ('session_id=foo,var; session_id=baz', list[str], True, ['foo,var', 'baz']),
        ('session_id=foo,var; session_id=baz', list[str], False, ['foo', 'var']),
        ('session_id=foo,var; session_id=baz', dict, True, dict()),
        ('session_id=foo,var; session_id=baz', dict, False, {'foo': 'var'}),
        ('session_id=foo,var; session_id=baz', str, True, 'foo,var'),
        ('session_id=foo,var; session_id=baz', str, False, 'foo,var'),
        ('session_id=foo; session_id=var', list[str], True, ['foo', 'var']),
        ('session_id=foo; session_id=var', list[str], False, ['foo']),
        ('session_id=foo; session_id=var', dict, True, dict()),
        ('session_id=foo; session_id=var', dict, False, {'foo': ''}),
        ('session_id=foo; session_id=var', str, True, 'foo'),
        ('session_id=foo; session_id=var', str, False, 'foo'),
        ('session_id=foo,var', list[str], True, ['foo,var']),
        ('session_id=foo,var', dict, True, dict()),
        ('session_id=foo,var', list[str], False, ['foo', 'var']),
        ('session_id=foo,var', dict, False, {'foo': 'var'}),
        ('session_id=foo,var', str, True, 'foo,var'),
        ('session_id=foo,var', str, False, 'foo,var'),
        ('session_id=foo', list[str], True, ['foo']),
        ('session_id=foo', list[str], False, ['foo']),
        ('session_id=foo', dict, False, {'foo': ''}),
        ('session_id=foo', str, True, 'foo'),
        ('session_id=foo', str, False, 'foo'),
        ('session_id=', list[str], True, ['']),
        ('session_id=', list[str], False, []),
        ('session_id=', dict, False, dict()),
        ('session_id=', str, True, ''),
        ('session_id=', str, False, ''),
        ('', list[str], True, ftr_fields.Unset),
        ('', list[str], False, ftr_fields.Unset),
        ('', dict, True, ftr_fields.Unset),
        ('', str, True, ftr_fields.Unset),
        ('', str, False, ftr_fields.Unset),
    ]
)
@pytest.mark.parametrize('standalone', [True, False])
def test_cookie_field(flask_app_auto, standalone, cookie, annotation, explode, expected):
    with flask_app_auto.test_request_context('/'):
        headers = [('Cookie', cookie)]
        builder = werkzeug.test.EnvironBuilder(path='/', headers=headers)
        env = builder.get_environ()
        request = werkzeug.wrappers.Request(env)
        with mock.patch('flask.request', request):
            field = ftr_fields.Cookie(alias='session_id', explode=explode)
            if standalone:
                field.annotation = annotation
                assert field.value == expected
            else:
                field.annotation = pydantic.create_model('QueryModel', session_id=(annotation, ...))
                if expected == ftr_fields.Unset:
                    assert field.value == dict()
                else:
                    assert field.value == {'session_id': expected}


@pytest.mark.parametrize('style', ['simple', 'spaceDelimited', 'pipeDelimited'])
def test_cookie_field_bad_style(style):
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        ftr_fields.Cookie(style=style)


@pytest.mark.parametrize('headers, annotation, expected', [
    ((('Auth', 'token1,token2'),), list[str], ['token1', 'token2']),
    ((('Auth', 'token1'),), list[str], ['token1']),
    ((('Auth', ''),), list[str], []),
    ((), list[str], ftr_fields.Unset),
    ((('Auth', 'token1'), ('Auth', 'token2')), list[str], ['token1', 'token2']),
])
@pytest.mark.parametrize('explode', [None, True, False])
def test_header_standalone_field(flask_app_auto, explode, headers, annotation, expected):
    with flask_app_auto.test_request_context('/', headers=headers):
        obj = ftr_fields.Header(alias='Auth', explode=explode)
        obj.annotation = annotation
        assert obj.value == expected


@pytest.mark.parametrize('style', ['form', 'spaceDelimited', 'pipeDelimited'])
def test_header_field_bad_style(style):
    with pytest.raises(ftr_errors.InvalidParameterTypeError):
        ftr_fields.Header(style=style)


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
    (str, ftr_fields.ValueType.string),
    (list, ftr_fields.ValueType.array),
    (list[str], ftr_fields.ValueType.array),
    (typing.List[str], ftr_fields.ValueType.array),  # noqa UP006
    (set, ftr_fields.ValueType.array),
    (set[str], ftr_fields.ValueType.array),
    (typing.Set[str], ftr_fields.ValueType.array),  # noqa UP006
    (frozenset, ftr_fields.ValueType.array),
    (frozenset[str], ftr_fields.ValueType.array),
    (typing.FrozenSet[str], ftr_fields.ValueType.array),  # noqa UP006
    (tuple, ftr_fields.ValueType.array),
    (tuple[str], ftr_fields.ValueType.array),
    (typing.Tuple[str], ftr_fields.ValueType.array),  # noqa UP006
    (dict, ftr_fields.ValueType.object),
    (dict[str, str], ftr_fields.ValueType.object),
    (typing.Dict[str, str], ftr_fields.ValueType.object),  # noqa UP006
    (pydantic.create_model('Model'), ftr_fields.ValueType.object),
    (typing.Annotated[str, pydantic.Field(alias='field')], ftr_fields.ValueType.string),
    (typing.Annotated[list[str], pydantic.Field(alias='list-field')], ftr_fields.ValueType.array),
    (typing.Annotated[typing.List[str], pydantic.Field(alias='list-field')], ftr_fields.ValueType.array),  # noqa UP006
])
def test_value_type_typeof(annotation, expected):
    assert ftr_fields.ValueType.typeof(annotation) == expected
