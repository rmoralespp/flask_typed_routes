"""
Contains the field classes that are used to define the
input fields of the API.
"""

import abc
import collections

import flask
import pydantic.fields

Unset = object()
Undef = pydantic.fields.PydanticUndefined


class FieldTypes:
    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"
    body = "body"


class Field(abc.ABC):
    """
    Abstract base class for all field types.
    Inherit from ABC with abstractmethod to avoid instantiation of this class.
    """

    kind = None

    def __init__(self, *args, embed=False, multi=False, **kwargs):
        self.embed = embed  # "JsonBody" fields can be embedded
        self.multi = multi  # "Header" and "Cookie" fields can have multiple values
        self.field_info = pydantic.fields.Field(*args, **kwargs)

    @property
    @abc.abstractmethod
    def value(self):
        raise NotImplementedError

    @property
    def alias(self):
        return self.field_info.alias

    @alias.setter
    def alias(self, value):
        self.field_info.alias = value

    def set_default(self, is_required, default):
        self.field_info.default = Undef if is_required else default

    def fetch(self, data):
        return data.get(self.alias, Unset) if self.alias else data


class Path(Field):
    kind = FieldTypes.path

    @property
    def value(self):
        return self.fetch(flask.request.view_args)


class Query(Field):
    kind = FieldTypes.query

    @property
    def value(self):
        return self.fetch(flask.request.args.to_dict(flat=not self.multi))


class Cookie(Field):
    kind = FieldTypes.cookie

    @property
    def value(self):
        return self.fetch(flask.request.cookies.to_dict(flat=not self.multi))


class Header(Field):
    kind = FieldTypes.header

    @property
    def value(self):
        items = flask.request.headers.items()
        if self.multi:
            data = collections.defaultdict(list)
            for k, v in items:
                data[k].append(v)
        else:
            data = dict(items)
        return self.fetch(data)


class JsonBody(Field):
    kind = FieldTypes.body

    @property
    def value(self):
        return self.fetch(flask.request.json or dict())
