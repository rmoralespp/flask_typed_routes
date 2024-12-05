# Query parameters

Parameters not included in the **Path** are automatically treated as **Query** parameters.

- **Required:** Declared as function arguments without default values.
- **Optional:** Declared with default values.

```python
import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.route('/items/')
def get_items(needy: str, skip: int = 0, limit: int = 100):
    data = {
        'needy': needy,
        'skip': skip,
        'limit': limit,
    }
    return flask.jsonify(data)
```

**Validation:**

- `needy`: **Required** and must be a string.
- `skip`: **Optional** and must be an integer. If not included, it defaults to 0.
- `limit`: **Optional** and must be an integer. If not included, it defaults to 100.


**Example request:** `GET http://127.0.0.1:5000/items/?needy=passed&skip=20`

```json
{
  "limit": 100,
  "needy": "passed",
  "skip": 20
}
```

**Bad request example:** If `needy` is not included in the request `http://127.0.0.1:5000/items/`

```json
{
  "errors": [
    {
      "input": {},
      "loc": [
        "query",
        "needy"
      ],
      "msg": "Field required",
      "type": "missing",
      "url": "https://errors.pydantic.dev/2.9/v/missing"
    }
  ]
}
```

## Additional validations

You can leverage Pydantic's custom [types](https://docs.pydantic.dev/latest/concepts/types/) or define your own custom
data [types](https://docs.pydantic.dev/latest/concepts/types/#custom-types) to apply additional validation to your query parameters.

```python
import typing as t

import annotated_types as at
import flask
import pydantic

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

# Custom Types for additional validation combining Pydantic and Annotated
Needy = t.Annotated[str, at.MinLen(3), at.MaxLen(10)]
Limit = t.Annotated[int, at.Ge(1), at.Le(100), pydantic.Field(alias="size")]

@app.route('/items/')
def get_items(needy: Needy, skip: int = 0, limit: Limit = 100):
    data = {
        'needy': needy,
        'skip': skip,
        'limit': limit,
    }
    return flask.jsonify(data)
```

Alternatively, you can use the `Query` field. This field is an extension of Pydantic's [field](https://docs.pydantic.dev/latest/concepts/fields/), 
offering powerful validation capabilities.
This flexibility allows you to tailor query parameter validation to your application's specific needs.

!!! tip
    The `Query` field is supported aliasing. You can use the `alias` argument to define 
    the query parameter name in the request.

```python
import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

Needy = t.Annotated[str, ftr.Query(min_length=3, max_length=10)]
Limit = t.Annotated[int, ftr.Query(ge=1, le=100, alias="size")]

@app.route('/items/')
def get_items(needy: Needy, skip: int = 0, limit: Limit = 100):
    data = {
        'needy': needy,
        'skip': skip,
        'limit': limit,
    }
    return flask.jsonify(data)
```

**Validation:**

- `needy`: **Required** and must be a string between 3 and 10 characters.
- `skip`: **Optional** and must be an integer.
- `limit`: **Optional** and must be an integer between 1 and 100, and must be named `size` in the request.

**Example request:** `GET http://127.0.0.1:5000/items/?needy=passed&size=20`

```json
{
  "limit": 20,
  "needy": "passed",
  "skip": 0
}
```

## Pydantic models

If you have a group of query parameters that are related, you can create a Pydantic model to declare them.

This would allow you to re-use the model in multiple places and also to declare validations and metadata for all the
parameters at once.

```python
import typing as t

import pydantic
import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


class QueryParams(pydantic.BaseModel):
    status: bool
    skip: int = 0
    limit: int = 10
    tracking_number: t.Annotated[int, pydantic.Field(alias="tracking", le=3)] = 1
    payment_method: t.Literal["cash", "credit"] = "credit"


@app.get('/orders/<user_id>/')
def get_orders(
    user_id: int,
    params: t.Annotated[QueryParams, ftr.Query()]
):
    data = {'user_id': user_id, "params": params.model_dump()}
    return flask.jsonify(data)
```

!!! warning
    The `Query` field can only be directly specified in the **function signature**.
    When using Pydantic models, you must use **Pydantic's [fields](https://pydantic-docs.helpmanual.io/concepts/fields/)**.

**Example request:** `GET ttp://127.0.0.1:5000/orders/233/?status=true`

```json
{
  "params": {
    "limit": 10,
    "payment_method": "credit",
    "skip": 0,
    "status": true,
    "tracking_number": 1
  },
  "user_id": 233
}
```

## Multiple values

If you want to allow a query parameter to have multiple values, you can use the `multi=True` argument in the `Query`
field.

```python
import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

Tags = t.Annotated[list[str], ftr.Query(alias="tag", multi=True)]

@app.get('/users/<user_id>/')
def get_users(user_id: int, tags: Tags = ()):
    data = {'user_id': user_id, "tags": tags}
    return flask.jsonify(data)
```

**Example request:** `GET http://127.0.0.1:5000/users/123/?tag=hello&tag=world`

```json
{
  "tags": [
    "hello",
    "world"
  ],
  "user_id": 123
}
```