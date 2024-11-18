# Query parameters

Parameters not included in the "path" are automatically treated as "query" parameters.

```python
import typing as t

import flask

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/posts/')
def read_posts(needy: str, skip: int = 0, limit: t.Annotated[int, flask_tpr.Query(alias="max", le=100)] = 100):
    data = {
        'needy': needy,
        'skip': skip,
        'limit': limit,
    }
    return flask.jsonify(data)
```

Explanation:

- `needy`: Query parameter that must be included in the request and must be a string.
- `skip`: Query parameter that is optional and must be an integer. If not included, it defaults to 0.
- `limit`: Query parameter that is optional and must be a string. If not included, it defaults to 100. The parameter is
  validated using the library field `Query` with a maximum value of 100. The parameter is also aliased as `max`.

!!! note
    The alias is used to demonstrate how the library can support Pydantic's Field class.

Valid Request: `http://127.0.0.1:5000/posts/?needy=passed&max=20`

```json
{
  "limit": 20,
  "needy": "passed",
  "skip": 0
}
```

**Invalid Requests:**

**Case1** If "needy" is not included in the request: `http://127.0.0.1:5000/posts/`

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

**Case2** If "limit" (alias: "max") is greater than 100: `http://127.0.0.1:5000/posts/?needy=passed&max=1000`

```json
{
  "errors": [
    {
      "ctx": {
        "le": 100
      },
      "input": "1000",
      "loc": [
        "query",
        "max"
      ],
      "msg": "Input should be less than or equal to 100",
      "type": "less_than_equal",
      "url": "https://errors.pydantic.dev/2.9/v/less_than_equal"
    }
  ]
}
```

## Query parameters using Pydantic models

If you have a group of query parameters that are related, you can create a Pydantic model to declare them.

This would allow you to re-use the model in multiple places and also to declare validations and metadata for all the
parameters at once.

!!! note
    `Query` field is only used to declare the query parameters in the function signature, in Pydantic models, you can use
    the Pydantic's `Field` class to declare constraints and metadata.

```python
import typing as t

import flask
import pydantic

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


class QueryParams(pydantic.BaseModel):
    status: bool
    skip: int = 0
    limit: int = 10
    tracking_number: t.Annotated[int, pydantic.Field(alias="tracking", le=3)] = 1
    payment_method: t.Literal["cash", "credit"] = "credit"


@app.get('/orders/<user_id>/')
def get_orders(
    user_id: int,
    params: t.Annotated[QueryParams, flask_tpr.Query()]
):
    data = {'user_id': user_id, "params": params.model_dump()}
    return flask.jsonify(data)
```

Go to `http://127.0.0.1:5000/orders/233/?status=true`

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

## Query parameters with multiple values

!!! tip
    If you want to allow a query parameter to have multiple values, you can use the `multi=True` argument in the `Annotated`

```python
import typing as t

import flask

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.get('/users/<user_id>/')
def get_users(
    user_id: int,
    tags: t.Annotated[list[str], flask_tpr.Query(alias="tag", multi=True)] = (),
):
    data = {'user_id': user_id, "tags": tags}
    return flask.jsonify(data)
```

Go to `http://127.0.0.1:5000/users/123/?tag=hello&tag=world`

```json
{
  "tags": [
    "hello",
    "world"
  ],
  "user_id": 123
}
```