"""
Contains the field classes that are used to define the
input fields of the API.
"""

import abc
import inspect
import typing as t

import flask
import pydantic.fields

import flask_typed_routes.errors as ftr_errors
import flask_typed_routes.utils as ftr_utils

Unset = object()
Undef = pydantic.fields.PydanticUndefined


def split_by(value, sep, /):
    return list(filter(None, map(str.strip, value.split(sep))))


def get_locator(alias, name, /):
    return alias or name


class NonExplodedArrayStyles:
    form = "form"  # comma-separated values
    simple = "simple"  # comma-separated values
    space_delimited = "spaceDelimited"  # space-separated
    pipe_delimited = "pipeDelimited"  # pipeline-separated

    @classmethod
    def choices(cls):
        return [cls.form, cls.simple, cls.space_delimited, cls.pipe_delimited]

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
    array_types = (list, t.List, tuple, t.Tuple, set, t.Set, frozenset, t.FrozenSet)  # noqa UP006

    __slots__ = ("embed", "style", "explode", "field_info", "annotation", "name")

    def __init__(self, *args, embed=False, style=None, explode=None, **kwargs):
        """
        Initialize the field with the given parameters.

        :param args:  Positional arguments for the Pydantic field.
        :param bool embed:  Embed the field in the parent model.
        :param Optional[str]:  OpenApi Serialization style for the field.
        :param Optional[bool] explode:  OpenApi Serialization explodes for the field.
        :param kwargs:  Keyword arguments for the Pydantic field.
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
        # These attributes are set by the `flask_typed_routes.core.parse_field` function
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

    def get_value(self, obj, /):
        """Get values from the request according to the field annotation."""

        if ftr_utils.is_subclass(self.annotation, pydantic.BaseModel):
            result = self.get_model_value(obj)
        else:
            result = self.get_alias_value(self.alias, obj, self.is_multi(self.annotation))
        return result

    def get_alias_value(self, alias, obj, is_multi, /):
        """Get request values when the annotation is a standard type according to the field alias."""

        raise NotImplementedError

    def get_model_value(self, obj, /):
        """Get request values when the annotation is a Pydantic model."""

        result = dict()
        for name, info in self.annotation.model_fields.items():
            alias = get_locator(info.alias, name)
            if alias in obj:
                result[alias] = self.get_alias_value(alias, obj, self.is_multi(info.annotation))
        return result

    @classmethod
    def is_multi(cls, annotation, /):
        """
        Check if the annotation is a data estructure (like an array)
        containing multiple values.
        """

        if annotation:
            tp = t.get_args(annotation)[0] if ftr_utils.is_annotated(annotation) else annotation
            return tp in cls.array_types or t.get_origin(tp) in cls.array_types
        else:
            return False


class Path(Field):
    kind = FieldTypes.path
    default_explode = False
    default_style = NonExplodedArrayStyles.simple
    supported_styles = (default_style,)

    @property
    def value(self):
        return self.get_alias_value(self.alias, flask.request.view_args, self.is_multi(self.annotation))

    def get_alias_value(self, alias, obj, is_multi, /):
        if alias not in obj:
            return Unset
        elif is_multi:
            return split_by(obj[alias], NonExplodedArrayStyles.get_sep(self.style))
        else:
            return obj[alias]


class Query(Field):
    kind = FieldTypes.query
    default_explode = True
    default_style = NonExplodedArrayStyles.form
    supported_styles = (
        default_style,
        NonExplodedArrayStyles.space_delimited,
        NonExplodedArrayStyles.pipe_delimited,
    )

    @property
    def value(self):
        return self.get_value(flask.request.args)

    def get_alias_value(self, alias, obj, is_multi, /):
        if alias not in obj:
            return Unset
        if is_multi and self.explode:
            return obj.getlist(alias)
        elif is_multi:
            return split_by(obj[alias], NonExplodedArrayStyles.get_sep(self.style))
        else:
            return obj[alias]


class Cookie(Query):
    kind = FieldTypes.cookie
    default_explode = True
    default_style = NonExplodedArrayStyles.form
    supported_styles = (default_style,)

    @property
    def value(self):
        return self.get_value(flask.request.cookies)


class Header(Field):
    kind = FieldTypes.header
    default_explode = False
    default_style = NonExplodedArrayStyles.simple
    supported_styles = (default_style,)

    @property
    def value(self):
        return self.get_value(flask.request.headers)

    def get_alias_value(self, alias, obj, is_multi, /):
        if alias not in obj:
            return Unset
        elif is_multi:
            return split_by(obj[alias], NonExplodedArrayStyles.get_sep(self.style))
        else:
            return obj[alias]


class Body(Field):
    kind = FieldTypes.body

    @property
    def value(self):
        data = flask.request.json or dict()
        return data.get(self.alias, Unset) if self.alias else data
