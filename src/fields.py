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


class Field:
    kind = None

    def __init__(self, *args, embed=False, multi=False, **kwargs):
        self.embed = embed
        self.multi = multi
        self.field_info = pydantic.fields.Field(*args, **kwargs)

    @property
    def value(self):
        return Unset

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
