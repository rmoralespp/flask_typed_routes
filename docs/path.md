# Path Parameters

You can validate **Path parameters** in your route by adding standard type hints to the function signature. 
`flask_typed_routes` ensures that parameters are correctly converted and validated based on their type annotations.

!!! warning
    If no type hint is provided, the **Path parameters** are not validated.

## Basic Usage

```python
import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.route('/items/<category_id>/<lang>/')
def read_items(category_id: int, lang: t.Literal['es', 'en']):
    data = {'category_id': category_id, 'lang': lang}
    return flask.jsonify(data)
```

**How It Works:**

- `category_id` is automatically converted to an integer.
- `lang` is restricted to the values 'es' or 'en'.

✅ **Valid request** `GET http://127.0.0.1:5000/items/12/es`

```json
{
  "category_id": 12,
  "lang": "es"
}
```

❌ **Bad request:** (wrong type for `category_id`) `GET http://127.0.0.1:5000/items/abc/es`

```json
{
  "errors": [
    {
      "input": "abc",
      "loc": [
        "path",
        "category_id"
      ],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "type": "int_parsing",
      "url": "https://errors.pydantic.dev/2.9/v/int_parsing"
    }
  ]
}
```

## Custom Validations

You can apply additional validation using Pydantic's custom [types](https://docs.pydantic.dev/latest/concepts/types/) 
with constraints, or define your own custom data [types](https://docs.pydantic.dev/latest/concepts/types/#custom-types)

```python
import typing as t

import annotated_types as at
import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.route('/items/<category_id>/')
def read_items(category_id: t.Annotated[int, at.Ge(1), at.Le(100)]):
    data = {'category_id': category_id}
    return flask.jsonify(data)
```

Alternatively, you can use the `Path` field. This field is an extension of Pydantic's [field](https://docs.pydantic.dev/latest/concepts/fields/), 
offering powerful validation capabilities.
This flexibility allows you to tailor path parameter validation to your application's specific needs.

```python
import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.route('/items/<category_id>/')
def read_items(category_id: t.Annotated[int, ftr.Path(ge=1, le=100)]):
    data = {'category_id': category_id}
    return flask.jsonify(data)
```

**Validation Rules:**

- `category_id` must be an integer between 1 and 100.

## Aliasing

!!! warning
    Aliases defined in Path type hints are ignored to maintain consistency with the Flask route parameter names.

## Arrays in Path Parameters

Path parameters can be parsed as **Arrays** using `set`, `tuple`, or `list`.
The library follows the `simple` style of **OpenAPI** parameter serialization for arrays, using commas as separators.

!!! tip 
    You can use the `set` type hint to validate that the values are unique.

```python
import flask

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.get('/users/<user_ids>/')
def get_users(user_ids: list[int]):
    return flask.jsonify({'user_ids': user_ids})
```

**Example request:** `GET http://127.0.0.1:5000/users/1,2,3/`

```json
{
  "user_ids": [1, 2, 3]
}
```

## Objects in Path Parameters

Path parameters can be parsed as **Objects** using dictionaries or Pydantic models.
The library follows the `simple` style of **OpenAPI** parameter serialization for objects.

**Using a Dictionary:**

```python
import flask

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.get('/users/<user_info>/')
def get_users(user_info: dict[str, str]):
    return flask.jsonify({'user_info': user_info})
```

**Example request:** `GET http://127.0.0.1:5000/users/role,admin,first_name,Alex`

```json
{
  "user_info": {
    "role": "admin",
    "first_name": "Alex"
  }
}
```

**Using a Pydantic model**:

```python
import typing as t

import flask
import pydantic

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


class User(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")  # Prevents extra fields
    name: str
    age: int = 100


@app.get('/users/<user_info>/')
def get_users(user_info: t.Annotated[User, ftr.Path()]):
    return flask.jsonify({'user_info': user_info.model_dump()})
```

**Example request:** `GET http://127.0.0.1:5000/users/name,Alex,age,25/`

```json
{
  "user_info": {
    "age": 25,
    "name": "Alex"
  }
}
```

**Handling Extra Fields**

The `extra="forbid"` configuration prevents additional fields:

`GET http://127.0.0.1:5000/users/name,Alex,age,25,role,Admin/`

```json
{
  "errors": [
    {
      "input": "Admin",
      "loc": [
        "path",
        "user_info",
        "role"
      ],
      "msg": "Extra inputs are not permitted",
      "type": "extra_forbidden",
      "url": "https://errors.pydantic.dev/2.10/v/extra_forbidden"
    }
  ]
}
```

**Handling incomplete key-value pairs**

If the number of key-value pairs is not even, the library uses the last key as a key with an empty value,
for example: `GET 127.0.0.1:5000/users/name,`

```json
{
  "user_info": {
    "age": 100,
    "name": ""
  }
}
```

**Handling Exploded parameter**

With `explode=True`, keys and values are separated by `=` in the URL.

```python
import typing as t

import flask

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

@app.get('/users/<user_info>/')
def get_users(user_info: t.Annotated[dict, ftr.Path(explode=True)]):
    return flask.jsonify({'user_info': user_info})
```

✅ **Example Request** `GET http://127.0.0.1:5000/users/name=Alex,age=25,role=Admin`

```json
{
  "user_info": {
    "name": "Alex",
    "age": "25",
    "role": "Admin"
  }
}
```

**Incorrect Parsing**

If you pass `explode=True`, the library misinterprets this structure:

❌ GET `http://127.0.0.1:5000/users/name,Alex,age,25,role,Admin/`

The result is a dictionary with empty values because the library interprets the comma as a separator.


```json
{
  "user_info": {
    "25": "",
    "Admin": "",
    "Alex": "",
    "age": "",
    "name": "",
    "role": ""
  }
}
```