# Request Body

To declare a request body, you use Pydantic models with all their power and benefits

!!! note
    By default, the library interprets a Pydantic model used as a type annotation in a function signature as a 
    request body model. However, if you only want to validate specific fields in the request body, you can use the
    `JsonBody()` annotation.

Basic Usage of request Body Validation:

```python
import typing as t

import flask
import pydantic

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


class Item(pydantic.BaseModel):
    title: str
    author: str


@app.post('/items/')
def create_item(item: Item):
    # Use Pydantic model to validate the request body
    return flask.jsonify(item.model_dump())


@app.put('/items/<item_id>/')
def update_item(
    item_id: int,
    title: t.Annotated[str, flask_tpr.JsonBody()] = None,
    author: t.Annotated[str, flask_tpr.JsonBody()] = None,
):
    # Use `JsonBody` to validate specific fields in the request body
    data = {
        'item_id': item_id,
        'title': title,
        'author': author,
    }
    return flask.jsonify(data)
```

**Explanation:**

- `Item`: Pydantic model that represents the structure of the request body. The model has two fields: `title` and
  `author`.
- `create_item`: Route that accepts a POST request with a JSON body that must match the `Item` model.
- `update_item`: Route that accepts a URL parameter `item_id` that must be an integer. The route also accepts two
  optional JSON body parameters: `title` and `author`. The parameters are validated using the library field `JsonBody`.

**Create a new Item**

Invalid request Body: `POST http://127.0.0.1:5000/items/`

```json
{
  "title": "Hello, World!"
}
```

Http Response:

```json
{
  "errors": [
    {
      "input": {
        "title": "Hello, World!"
      },
      "loc": [
        "body",
        "author"
      ],
      "msg": "Field required",
      "type": "missing",
      "url": "https://errors.pydantic.dev/2.9/v/missing"
    }
  ]
}
```

**Update an Item**

Invalid request Body: `PUT http://127.0.0.1:5000/items/123`

```json
{
  "title": 111
}
```

Http Response:

```json
{
  "errors": [
    {
      "input": 111,
      "loc": [
        "body",
        "title"
      ],
      "msg": "Input should be a valid string",
      "type": "string_type",
      "url": "https://errors.pydantic.dev/2.9/v/string_type"
    }
  ]
}
```

### Using multiple Pydantic Models, `JsonBody` Field with `embed`

```python
import typing as t

import flask
import pydantic

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


class Item(pydantic.BaseModel):
    title: str
    author: str


class User(pydantic.BaseModel):
    email: str
    age: int


@app.post('/users/<user_id>/items/')
def create_item_by_user(
    user_id: int,
    item: t.Annotated[Item, flask_tpr.JsonBody(embed=True)],
    user: t.Annotated[User, flask_tpr.JsonBody(embed=True)],
):
    # Use `JsonBody` with `embed=True` to validate nested specific fields in the request body
    data = {
        'user_id': user_id,
        'item': item.model_dump(),
        'user': user.model_dump(),
    }
    return flask.jsonify(data)
```

**Request Body**

`POST http://127.0.0.1:5000/users/123/items/`

```json
{
  "item": {
    "title": "Hello, World!",
    "author": "John Doe"
  },
  "user": {
    "email": "myemail@abc.com",
    "age": 25
  }
}
```

**Http Response**

```json
{
  "item": {
    "author": "John Doe",
    "title": "Hello, World!"
  },
  "user": {
    "age": 25,
    "email": "myemail@abc.com"
  },
  "user_id": 123
}
```