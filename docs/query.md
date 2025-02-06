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

✅ **Valid request:** `GET http://127.0.0.1:5000/items/?needy=passed&skip=20`

```json
{
  "limit": 100,
  "needy": "passed",
  "skip": 20
}
```

❌ **Bad request:** If `needy` is not included in the request `http://127.0.0.1:5000/items/`

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

## Custom validations

You can apply additional validation using Pydantic's custom [types](https://docs.pydantic.dev/latest/concepts/types/) 
with constraints, or define your own custom data [types](https://docs.pydantic.dev/latest/concepts/types/#custom-types)

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

Alternatively, you can use the `Query` field. This field is an extension of
Pydantic's [field](https://docs.pydantic.dev/latest/concepts/fields/),
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

## Arrays in query parameters

If you want to allow a query parameter to parse as an **Array**, you can use `set`, `tuple`, or `list` annotations.

!!! tip
    You can use the `set` type hint to validate that the values are unique.

```python
import typing as t

import flask
import flask_typed_routes as ftr
import pydantic

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

Tags = t.Annotated[list[str], pydantic.Field(alias="tag")]


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

!!! note
    It is important to highlight that the previous URL contains multiple query parameters named `tag`.

!!! tip
    If the URL includes a **query parameter** with multiple values separated by commas, pipes(`|`), or spaces,
    the resulting list will contain a single element with the entire string.

    To retrieve each value separately, you need to set the `explode`
    parameter in the `Query` field and specify the `style` parameter to define the serialization format.

**Here’s an example of how to do it:**

```python
import typing as t

import flask

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

# By default, the 'style' is 'form', which means that the values are separated by commas.
TagsByComma = t.Annotated[list[str], ftr.Query(explode=False)]

# You can also use 'pipeDelimited' or 'spaceDelimited' as the 'style' to indicate another serialization style delimiter.
TagsBySpace = t.Annotated[list[str], ftr.Query(explode=False, style="spaceDelimited")]
TagsByPipe = t.Annotated[list[str], ftr.Query(explode=False, style="pipeDelimited")]


@app.get('/tags/comma/')
def get_tags_by_comma(tags: TagsByComma = ()):
    return flask.jsonify({"tags": tags})


@app.get('/tags/space/')
def get_tags_by_space(tags: TagsBySpace = ()):
    return flask.jsonify({"tags": tags})


@app.get('/tags/pipe/')
def get_tags_by_pipe(tags: TagsByPipe = ()):
    return flask.jsonify({"tags": tags})
```

**Example requests:**

* By commas: `http://localhost:5000/tags/comma/?tags=hello,world`
* By spaces: `http://localhost:5000/tags/space/?tags=hello world`
* By pipes: `http://localhost:5000/tags/pipe/?tags=hello|world`

You will see the JSON response as:

```json
{
  "tags": [
    "hello",
    "world"
  ]
}
```

## Object in a single query parameter

Query parameters can be parsed as **Objects** using dictionaries or Pydantic models.
The library follows the `form` style and of **OpenAPI** parameter serialization for objects.

The default serialization method is:

- **Style:** `form`
- **Explode:** `true`

The query parameter `info` is serialized as follows:

| style         | explode    | URL                                    |
|---------------|------------|----------------------------------------|
| form          | false      | /users?info=role,admin,first_name,Alex |
| pipeDelimited | true/false | n/a                                    |
| pipeDelimited | true/false | n/a                                    |

You can use `dict` or Pydantic models to parse object query parameters.

**Using a dictionary**

```python
import typing as t

import flask

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.get('/users/')
def get_users(info: t.Annotated[dict, ftr.Query(explode=False)]):
    return flask.jsonify({'info': info})
```

**Example request:** `GET http://127.0.0.1:5000/users/?info=role,admin,first_name,Alex`

```json
{
  "info": {
    "first_name": "Alex",
    "role": "admin"
  }
}
```

**Using Pydantic models**:

In this example, we use a Pydantic model to parse the query parameters and an embedded model to interpret the 
`info` query parameter as an object using `explode=False` with `form=style`.

The `explode` is set to `false` to parse the query parameter as an object, while the `style` defaults 
to `form`. The supported styles are `form`, `spaceDelimited`, and `pipeDelimited`, but only `form` is supported
for objects.

```python
import typing as t

import flask
import pydantic

import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


class UserInfo(pydantic.BaseModel):
    role: str
    first_name: str


class QueryParams(pydantic.BaseModel):
    info: UserInfo


@app.get('/users/')
def get_users(info: t.Annotated[QueryParams, ftr.Query(explode=False)]):
    return flask.jsonify({'info': info.model_dump()})
```

**Example request:** `GET http://127.0.0.1:5000/users/?info=role,admin,first_name,Alex`

```json
{
  "info": {
    "first_name": "Alex",
    "role": "admin"
  }
}
```
