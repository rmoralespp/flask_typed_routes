# Path Parameters

You can validate **Path parameters** in your route by adding standard type hints to the function signature.

!!! warning
    If no type hint is provided, the **Path parameters** are not validated.

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

**Conversion:** The library automatically converts path parameters to their specified types:

- `category_id` is converted to an integer, so your function receives it as an integer.
- `lang` is treated as a string, so your function receives it as a string.

**Validation:**

- `category_id` Must be an integer.
- `lang` Must be either 'es' or 'en'.

**Example request:** `GET http://127.0.0.1:5000/items/12/es`

```json
{
  "category_id": 12,
  "lang": "es"
}
```

**Bad request example:** If `category_id` is not an integer `GET http://127.0.0.1:5000/items/abc/es`

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

## Custom validations

You can leverage Pydantic's custom [types](https://docs.pydantic.dev/latest/concepts/types/) or define your own custom
data [types](https://docs.pydantic.dev/latest/concepts/types/#custom-types) to apply additional validation to your path parameters.

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

**Validation:**

- `category_id` must be an integer between 1 and 100.

## Aliasing

!!! warning
    Aliases defined in Path type hints will be ignored to maintain consistency with the names specified in the Flask route.


## Multiple values in a single path parameter

If you want to allow a query parameter to have multiple values, you can use `set`, `tuple`, or `list` annotations.

!!! note
    Path fields support the `simple` **OpenAPI** style, meaning they can handle multiple values separated by commas. 

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
  "user_ids": ["1", "2", "3"]
}
```

