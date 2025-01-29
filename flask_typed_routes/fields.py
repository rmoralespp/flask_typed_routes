"""
Contains the field classes that are used to define the
input fields of the API.
"""

import abc
import collections
import inspect
import typing as t

import flask
import pydantic.fields

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.utils as ftr_utils

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
    multi_types = (list, t.List, tuple, t.Tuple, set, t.Set, frozenset, t.FrozenSet) # noqa UP006

    __slots__ = ("embed", "field_info", "annotation", "name")

    def __init__(self, *args, embed=False, **kwargs):
        if embed and self.kind != FieldTypes.body:
            raise ftr_errors.InvalidParameterTypeError("Only 'Body' fields can be embedded.")

        self.embed = embed  # `Body` fields can be embedded
        self.field_info = pydantic.fields.Field(*args, **kwargs)
        # These attributes are set by the `flask_typed_routes.core.parse_field` function
        self.annotation = None
        self.name = None

    @property
    def locator(self):
        return self.alias or self.name

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

    @property
    def default(self):
        return self.field_info.default

    @default.setter
    def default(self, default):
        if default != inspect.Parameter.empty:
            self.field_info.default = default

    @property
    def is_required(self):
        return self.default == inspect.Parameter.empty

    @classmethod
    def is_multi_field(cls, annotation):
        """Check if the annotation is a multi-value type."""

        if annotation:
            tp = t.get_args(annotation)[0] if ftr_utils.is_annotated(annotation) else annotation
            return tp in cls.multi_types or t.get_origin(tp) in cls.multi_types
        else:
            return False

    def fetch_single_value(self, data):
        return data.get(self.alias, Unset) if self.alias else data

    def fetch_model_value(self, obj):
        data = dict()
        for name, info in self.annotation.model_fields.items():
            alias = info.alias or name
            if alias in obj:
                if self.is_multi_field(info.annotation):
                    data[alias] = obj.getlist(alias)
                else:
                    data[alias] = obj.get(alias)
        return data


class Path(Field):
    kind = FieldTypes.path

    @property
    def value(self):
        return self.fetch_single_value(flask.request.view_args)


class Query(Field):
    kind = FieldTypes.query

    @property
    def value(self):
        if ftr_utils.is_subclass(self.annotation, pydantic.BaseModel):
            return self.fetch_model_value(flask.request.args)
        else:
            flat = not self.is_multi_field(self.annotation)
            return self.fetch_single_value(flask.request.args.to_dict(flat=flat))


class Cookie(Field):
    kind = FieldTypes.cookie

    @property
    def value(self):
        if ftr_utils.is_subclass(self.annotation, pydantic.BaseModel):
            return self.fetch_model_value(flask.request.cookies)
        else:
            flat = not self.is_multi_field(self.annotation)
            return self.fetch_single_value(flask.request.cookies.to_dict(flat=flat))


class Header(Field):
    kind = FieldTypes.header

    @property
    def value(self):
        if ftr_utils.is_subclass(self.annotation, pydantic.BaseModel):
            return self.fetch_model_value(flask.request.headers)
        else:
            items = flask.request.headers.items()
            multi = self.is_multi_field(self.annotation)
            if multi:
                data = collections.defaultdict(list)
                for k, v in items:
                    data[k].append(v)
            else:
                data = dict(items)
            return self.fetch_single_value(data)


class Body(Field):
    kind = FieldTypes.body

    @property
    def value(self):
        return self.fetch_single_value(flask.request.json or dict())
