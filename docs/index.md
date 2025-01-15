[![CI](https://github.com/rmoralespp/flask_typed_routes/workflows/CI/badge.svg)](https://github.com/rmoralespp/flask_typed_routes/actions?query=event%3Arelease+workflow%3ACI)
[![pypi](https://img.shields.io/pypi/v/flask_typed_routes.svg)](https://pypi.python.org/pypi/flask_typed_routes)
[![codecov](https://codecov.io/gh/rmoralespp/jsonl/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rmoralespp/flask_typed_routes)
[![license](https://img.shields.io/github/license/rmoralespp/jsonl.svg)](https://github.com/rmoralespp/flask_typed_routes/blob/main/LICENSE)

## About

**flask_typed_routes** is a `Flask` extension designed to effortlessly validate requests with `Pydantic` based on
standard Python type hints.

## Features

- 🎯 **Type Safety:** Automatically validates requests using Python type hints.
- 🔌 **Easy Integration:** Simple extension for validating Flask routes.
- ⚠️ **Error Handling:** Clear and automatic responses for validation failures.
- ✨ **Autocomplete:** Editor integration with comprehensive suggestions.
- ⚙️ **Validation Modes:** Supports automatic validation for all routes and manual validation for specific routes using decorators.
- 📖 **OpenAPI Support:** Automatically generates an OpenAPI schema, ensuring clear documentation and seamless integration with OpenAPI tools.

## Requirements

- Python 3.10+
- Pydantic 2.0+
- Flask

## Installation

To install **flask_typed_routes** using `pip`, run the following command:

```bash
pip install flask_typed_routes
```

## Getting Started

This tool offers comprehensive validation for various types of request parameters,
including **Path, Query, Body, Header, and Cookie** parameters.

Example of a simple Flask application using `flask_typed_routes`:

Create a file `items.py` with:

```python
import typing as t

import annotated_types as at
import flask
import flask_typed_routes as ftr
import pydantic

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

Skip = pydantic.NonNegativeInt  # custom Pydantic type
Limit = t.Annotated[int, at.Ge(1), at.Le(100)]  # custom Annotated type


@app.get('/items/<user>/')
def get_items(user: str, skip: Skip = 0, limit: Limit = 10):
    # Parameters not included in the "path" are automatically treated as "query" parameters.
    data = {
        'user': user,
        'skip': skip,
        'limit': limit,
    }
    return flask.jsonify(data)
```

**Run the server with:**

```bash
flask --app items run --debug
```

Open your browser and go to `http://127.0.0.1:5000/items/myuser/?skip=20`
You will see the JSON response as:

```json
{
  "limit": 10,
  "skip": 20,
  "user": "myuser"
}
```

**Validation:** Open your browser and go to `http://127.0.0.1:5000/items/myuser/?skip=abc`
You will see the JSON response with the error details because the `skip` parameter is not an integer:

```json
{
  "errors": [
    {
      "input": "abc",
      "loc": [
        "query",
        "skip"
      ],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "type": "int_parsing",
      "url": "https://errors.pydantic.dev/2.9/v/int_parsing"
    }
  ]
}
```

### Example with Pydantic Models

You can also use Pydantic models to validate request data in Flask routes.
Now let's update the `items.py` file with:

```python
import flask
import flask_typed_routes as ftr
import pydantic

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


class Item(pydantic.BaseModel):
    name: str
    description: str = None
    price: float


@app.post('/items/')
def create_item(item: Item):
    return flask.jsonify(item.model_dump())


@app.put('/items/<item_id>/')
def update_item(item_id: int, item: Item):
    return flask.jsonify({'item_id': item_id, **item.model_dump()})
```

### Using Flask Blueprints

You can also use `flask_typed_routes` with Flask Blueprints.

Now let's update the `items.py` file with:

```python
import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)
blp = flask.Blueprint('items', __name__, url_prefix='/v2')


@blp.get('/items/')
def get_items_v2(skip: int = 0, limit: int = 10, country: str = 'US'):
    data = {'skip': skip, 'limit': limit, 'country': country}
    return flask.jsonify(data)


app.register_blueprint(blp)
```

### Using Flask Class-Based Views

You can also use `flask_typed_routes` with Flask Class-Based Views.

Now let's update the `items.py` file with:

```python
import flask
import flask.views
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


class UserProducts(flask.views.View):

    def dispatch_request(self, user: str, skip: int = 0, limit: int = 10):
        data = {'user': user, 'skip': skip, 'limit': limit}
        return flask.jsonify(data)


class UserOrders(flask.views.MethodView):

    def get(self, user: str, skip: int = 0, limit: int = 10):
        data = {'user': user, 'skip': skip, 'limit': limit}
        return flask.jsonify(data)


app.add_url_rule('/products/<user>/all/', view_func=UserProducts.as_view('user_products'))
app.add_url_rule('/orders/<user>/all/', view_func=UserOrders.as_view('user_orders'))
```

### Interactive API docs

You can OpenApi schema generated by `flask_typed_routes` with any OpenApi tools to
generate interactive API docs for your Flask application. In this example we will use the `swagger-ui-py` library.

```bash
pip install swagger-ui-py  # ignore if already installed
```

```python
import typing

import flask
import pydantic
import swagger_ui
import flask_typed_routes as ftr

app = flask.Flask(__name__)
app_ftr = ftr.FlaskTypedRoutes(app, title="Items API")
swagger_ui.api_doc(
    app,
    config_rel_url=app_ftr.openapi_url_json,
    url_prefix=app_ftr.openapi_url_prefix,
)


class Item(pydantic.BaseModel):
    name: str
    price: float
    status: typing.Literal['reserved', 'available']


@app.get("/items/<user_id>/")
def read_items(user_id: int, status: typing.Literal['reserved', 'available'] = 'available'):
    result = {"user_id": user_id, "status": status}
    return flask.jsonify(result)


@app.put("/items/<user_id>")
def update_item(item_id: int, item: Item):
    result = {"item_id": item_id, "item_name": item.name, "item_price": item.price}
    return flask.jsonify(result)
```

Open your browser and go to `http://127.0.0.1:5000/api/doc/`

**Read Items** endpoint:

![OpenApi Example](./openapi_example0.png)

**Update Item** endpoint:

![OpenApi Example](./openapi_example01.png)