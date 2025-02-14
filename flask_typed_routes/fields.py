# -*- coding: utf-8 -*-

"""
Contains the field classes that are used to define the
input fields of the API.
"""

import abc
import enum
import inspect
import typing as t
import uuid

import flask
import pydantic.fields

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.utils as ftr_utils

Unset = object()
Undef = pydantic.fields.PydanticUndefined

array_types = (list, t.List, tuple, t.Tuple, set, t.Set, frozenset, t.FrozenSet)  # noqa UP006
dict_types = (dict, t.Dict)  # noqa UP006


def is_json(metadata, /):
    return any(isinstance(m, pydantic.Json) for m in metadata)


def split_by(value, sep, /, maxsplit=-1):
    return list(filter(None, map(str.strip, value.split(sep, maxsplit=maxsplit))))


def split_by_pairs(value, main_sep, pair_sep, /, default=""):
    if main_sep == pair_sep:
        data = split_by(value, main_sep)
        if len(data) % 2 != 0:
            # If the data is not even, add a default value
            data.append(default)
        return dict(zip(data[::2], data[1::2], strict=False))
    else:
        data = dict()
        for pair_string in split_by(value, main_sep):
            pair = split_by(pair_string, pair_sep, maxsplit=1)
            if len(pair) == 2:
                data[pair[0]] = pair[1]
            elif len(pair) == 1:
                data[pair[0]] = default
        return data


def get_locator(alias, name, /):
    return alias or name


class DataType(enum.Enum):
    primitive = "primitive"  # "blue"
    object = "object"  # ["blue", "black", "brown"]
    array = "array"  # {"R": 100, "G": 200, "B": 150}

    @classmethod
    def belong_to(cls, annotation, types, /):
        if annotation:
            tp = t.get_args(annotation)[0] if ftr_utils.is_annotated(annotation) else annotation
            return tp in types or t.get_origin(tp) in types
        else:
            return False

    @classmethod
    def typeof(cls, annotation, metadata, /):
        if cls.belong_to(annotation, dict_types) or ftr_utils.is_subclass(annotation, pydantic.BaseModel):
            # Pydantic will handle the deserialization of the JSON string.
            return cls.primitive if is_json(metadata) else cls.object
        elif cls.belong_to(annotation, array_types):
            return cls.array
        else:
            return cls.primitive


class NonExplodedStyles:
    form = "form"  # comma-separated values
    simple = "simple"  # comma-separated values
    space_delimited = "spaceDelimited"  # space-separated
    pipe_delimited = "pipeDelimited"  # pipeline-separated

    @classmethod
    def choices(cls):
        return (cls.form, cls.simple, cls.space_delimited, cls.pipe_delimited)

    @classmethod
    def get_sep(cls, style):
        mapper = {
            cls.form: ",",
            cls.simple: ",",
            cls.space_delimited: " ",
            cls.pipe_delimited: "|",
        }
        return mapper[style]


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
    default_explode = None
    default_style = None
    supported_styles = ()

    __slots__ = ("embed", "style", "explode", "field_info", "annotation", "name")

    def __init__(self, *args, embed=False, style=None, explode=None, **kwargs):
        """
        Initialize the field with the given parameters.

        :param args: Positional arguments for the Pydantic field.
        :param bool embed: Embed the field in the parent model.
        :param Optional[str] style: Use the OpenAPI serialization "style" for the field.
        :param Optional[bool] explode: Use the OpenAPI serialization "explode" for the field.
        :param kwargs: Keyword arguments for the Pydantic field.
        """

        if embed and self.kind != FieldTypes.body:
            raise ftr_errors.InvalidParameterTypeError("Only 'Body' fields can be embedded.")

        # Set the style/explode serialization parameters for the field.
        if style and style not in self.supported_styles:
            raise ftr_errors.InvalidParameterTypeError(f"Unsupported style '{style}' for '{self.kind}' fields.")

        self.style = style or self.default_style
        self.explode = self.default_explode if explode is None else explode  # check explicit None

        self.embed = embed  # `Body` fields can be embedded
        self.field_info = pydantic.fields.Field(*args, **kwargs)
        # These attributes are established later.
        self.annotation = None
        self.name = None

    @property
    def locator(self):
        return get_locator(self.alias, self.name)

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
        # Only set the field's default value if the default function parameter is not empty.
        if default != inspect.Parameter.empty:
            self.field_info.default = default

    @property
    def is_required(self):
        return self.default != Undef

    @property
    def data_type(self, /):
        return DataType.typeof(self.annotation, self.field_info.metadata)

    @property
    def is_model_object(self, /):
        return self.data_type == DataType.object and ftr_utils.is_subclass(self.annotation, pydantic.BaseModel)

    def get_value(self, obj, /):
        """Get values from the request according to the field annotation."""

        if self.is_model_object:
            return self.get_model_value(obj)
        else:
            return self.get_alias_value(self.alias, obj, self.data_type)

    def get_alias_value(self, alias, obj, data_type, /):
        """Get request values when the annotation is a standard type according to the field alias."""

        raise NotImplementedError

    def get_model_value(self, obj, /):
        """Get request values when the annotation is a Pydantic model."""

        result = dict()
        for name, info in self.annotation.model_fields.items():
            alias = get_locator(info.alias, name)
            if alias in obj:
                result[alias] = self.get_alias_value(alias, obj, DataType.typeof(info.annotation, info.metadata))
        return result

    def get_simple_alias_value(self, alias, obj, data_type, /):
        main_sep = NonExplodedStyles.get_sep(NonExplodedStyles.simple)
        if alias not in obj:
            return Unset
        elif data_type == DataType.array:
            return split_by(obj[alias], main_sep)
        elif data_type == DataType.object:
            raw = obj[alias]
            pair_sep = "=" if self.explode else main_sep
            return split_by_pairs(raw, main_sep, pair_sep)
        else:
            return obj[alias]


class Path(Field):
    kind = FieldTypes.path
    default_explode = False
    default_style = NonExplodedStyles.simple
    supported_styles = (default_style,)

    @property
    def value(self):
        return self.get_alias_value(self.alias, flask.request.view_args, self.data_type)

    def get_alias_value(self, alias, obj, data_type, /):
        return self.get_simple_alias_value(alias, obj, data_type)


class Query(Field):
    kind = FieldTypes.query
    default_explode = True
    default_style = NonExplodedStyles.form
    supported_styles = (
        default_style,
        NonExplodedStyles.space_delimited,
        NonExplodedStyles.pipe_delimited,
    )

    @property
    def value(self):
        return self.get_value(flask.request.args)

    def get_alias_value(self, alias, obj, data_type, /):
        sep = NonExplodedStyles.get_sep(self.style)
        if alias not in obj:
            return Unset
        if data_type == DataType.array:
            if self.explode:
                return obj.getlist(alias)
            else:
                return split_by(obj[alias], sep)
        elif data_type == DataType.object:
            if self.style == NonExplodedStyles.form and not self.explode:
                return split_by_pairs(obj[alias], sep, sep)
            else:
                return dict()
        else:
            return obj[alias]


class Cookie(Query):
    kind = FieldTypes.cookie
    default_explode = True
    default_style = NonExplodedStyles.form
    supported_styles = (default_style,)

    @property
    def value(self):
        return self.get_value(flask.request.cookies)


class Header(Field):
    kind = FieldTypes.header
    default_explode = False
    default_style = NonExplodedStyles.simple
    supported_styles = (default_style,)

    @property
    def value(self):
        return self.get_value(flask.request.headers)

    def get_alias_value(self, alias, obj, data_type, /):
        return self.get_simple_alias_value(alias, obj, data_type)


class Body(Field):
    kind = FieldTypes.body

    @property
    def value(self):
        data = flask.request.json or dict()
        return data.get(self.alias, Unset) if self.alias else data


class Depends(Field):

    def __init__(self, dependency, /, use_cache=False):
        """
        Initialize the field with the given parameters.

        :param Callable dependency: Dependency function to get the value.
        :param bool use_cache:
            By default, `use_cache` is set to `False` so that the dependency is called again
            (if declared more than once) in the same request.

            Set `use_cache` to `False` so that after a dependency is called for the first time in a request,
            if the dependency is declared again for the rest of the request
        """

        super().__init__()
        self._dependency = dependency
        self._use_cache = use_cache
        self._ref = "{}-{}".format("dependency", uuid.uuid4())

    @property
    def value(self):
        if self._use_cache:
            if self._ref in flask.g:
                result = getattr(flask.g, self._ref)
            else:
                result = self._dependency()
                setattr(flask.g, self._ref, result)
            return result
        else:
            return self._dependency()
