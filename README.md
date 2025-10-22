[![CI](https://github.com/rmoralespp/flask_typed_routes/workflows/CI/badge.svg)](https://github.com/rmoralespp/flask_typed_routes/actions?query=event%3Arelease+workflow%3ACI)
[![pypi](https://img.shields.io/pypi/v/flask_typed_routes.svg)](https://pypi.python.org/pypi/flask_typed_routes)
[![codecov](https://codecov.io/gh/rmoralespp/flask_typed_routes/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rmoralespp/flask_typed_routes)
[![license](https://img.shields.io/github/license/rmoralespp/flask_typed_routes.svg)](https://github.com/rmoralespp/flask_typed_routes/blob/main/LICENSE)
[![Downloads](https://pepy.tech/badge/flask_typed_routes)](https://pepy.tech/project/flask_typed_routes)

<div align="center">
    <a href="https://rmoralespp.github.io/flask_typed_routes/" target="_blank">
        <img class="off-glb" src="https://raw.githubusercontent.com/rmoralespp/flask_typed_routes/main/docs/images/logo.svg" 
             width="20%" height="auto" alt="logo">
    </a>
</div>
<div align="center"><b>Validate requests with Pydantic based on standard Python type hints.</b></div>

## About 

**flask_typed_routes** is a `Flask` extension designed to effortlessly validate requests with `Pydantic` based on standard Python type hints.

**Documentation**: https://rmoralespp.github.io/flask_typed_routes/

## Features

- **Easy:** Easy to use and integrate with [Flask applications](https://flask.palletsprojects.com).
- **Standard-based:** Based on [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)
- **Data validation:** Fast data verification based on [Pydantic](https://docs.pydantic.dev/)

## Requirements

- Python 3.10+
- Pydantic >=2.0.0, <2.12.0
- Flask

## Installation

To install **flask_typed_routes** using `pip`, run the following command:

```bash
pip install flask_typed_routes
```

## Getting Started

This tool allows you to validate request parameters in Flask, similar to how FastAPI handles validation. It supports 
**Path**, **Query**, **Header**, **Cookie**, and **Body** validation.


## Example

Create a file `items.py` with:

```python
import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app=app)


@app.get("/")
def read_root():
    return flask.jsonify({"Hello": "World"})


@app.get("/items/<user>/")
def read_items(user: str, skip: int = 0, limit: int = 10):
    return flask.jsonify({"user": user, "skip": skip, "limit": limit})
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

### Example Body Validation

You can also use Pydantic models to validate the request body.

Now let's update the `items.py` file with:

```python
import flask
import flask_typed_routes as ftr
import pydantic


app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app=app)


class Item(pydantic.BaseModel):
    name: str
    price: float
    description: str = None


@app.get("/")
def read_root():
    return flask.jsonify({"Hello": "World"})


@app.get("/items/<user>/")
def read_items(user: str, skip: int = 0, limit: int = 10):
    return flask.jsonify({"user": user, "skip": skip, "limit": limit})


@app.post('/items/')
def create_item(item: Item):
    return flask.jsonify(item.model_dump())


@app.put('/items/<item_id>/')
def update_item(item_id: int, item: Item):
    return flask.jsonify({'item_id': item_id, **item.model_dump()})
```

### Example Flask Blueprints

Now let's update the `items.py` file with:

```python
import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app=app)
orders = flask.Blueprint('orders', __name__)


@orders.get("/orders/<user>/")
def read_orders(user: str, skip: int = 0, limit: int = 10):
    return flask.jsonify({"user": user, "skip": skip, "limit": limit})


app.register_blueprint(orders)
```

### Example Flask Class-Based Views

Now let's update the `items.py` file with:

```python
import flask
import flask.views
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app=app)


class UserProducts(flask.views.View):

    def dispatch_request(self, user: str, skip: int = 0, limit: int = 10):
        data = {'user': user, 'skip': skip, 'limit': limit}
        return flask.jsonify(data)


class UserOrders(flask.views.MethodView):

    def get(self, user: str, skip: int = 0, limit: int = 10):
        data = {'user': user, 'skip': skip, 'limit': limit}
        return flask.jsonify(data)


app.add_url_rule('/products/<user>/', view_func=UserProducts.as_view('user_products'))
app.add_url_rule('/orders/<user>/', view_func=UserOrders.as_view('user_orders'))
```

### Interactive API docs

You can generate interactive API docs for your Flask application using OpenAPI schema generated by `flask_typed_routes`
with any OpenAPI UI library. For example, you can use `swagger-ui-py` to generate the API docs.

```bash
pip install swagger-ui-py  # ignore if already installed
```

```python
import flask
import flask_typed_routes as ftr
import pydantic
import swagger_ui

app = flask.Flask(__name__)
app_ftr = ftr.FlaskTypedRoutes(app=app)


class Item(pydantic.BaseModel):
    name: str
    price: float
    description: str = None


@app.get('/items/<user>/')
def read_items(user: str, skip: int = 0, limit: int = 10):
    data = {'user': user, 'skip': skip, 'limit': limit}
    return flask.jsonify(data)


@app.post('/items/')
def create_item(item: Item):
    return flask.jsonify(item.model_dump())


@app.put('/items/<item_id>/')
def update_item(item_id: int, item: Item):
    return flask.jsonify({'item_id': item_id, **item.model_dump()})


@app.delete('/items/<item_id>/')
def remove_item(item_id: int):
    return flask.jsonify({'item_id': item_id})


swagger_ui.api_doc(app, config=app_ftr.get_openapi_schema(), url_prefix='/docs')
```

Open your browser and go to `http://127.0.0.1:5000/docs/`

![OpenApi Example](https://raw.githubusercontent.com/rmoralespp/flask_typed_routes/main/docs/images/openapi1.png)

**Create item** endpoint:

![OpenApi Example](https://raw.githubusercontent.com/rmoralespp/flask_typed_routes/main/docs/images/openapi2.png)

**Read Items** endpoint:

![OpenApi Example](https://raw.githubusercontent.com/rmoralespp/flask_typed_routes/main/docs/images/openapi3.png)

## Documentation

For more detailed information and usage examples, refer to the
project [documentation](https://rmoralespp.github.io/flask_typed_routes/)

## Development

To contribute to the project, you can run the following commands for testing and documentation:

### Setting up the Development Environment

Ensure you have PIP updated:

```bash
python -m pip install --upgrade pip
```

### Running Unit Tests

Install the development dependencies and run the tests:

```bash
pip install --group=test --upgrade  # Skip if already installed
python -m pytest tests/
python -m pytest --cov  # With coverage report
```

### Running the Linter
To run the linter, use the following command:

```bash
pip install --group=lint --upgrade  # Skip if already installed
ruff check .
```

### Building the Documentation

To build the documentation locally, use the following commands:

```bash
pip install --group=doc --upgrade  # Skip if already installed
mkdocs serve  # Start live-reloading docs server
mkdocs build  # Build the documentation site
```

## License

This project is licensed under the [MIT license](LICENSE).
