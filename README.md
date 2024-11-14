[![CI](https://github.com/rmoralespp/flask_typed_routes/workflows/CI/badge.svg)](https://github.com/rmoralespp/flask_typed_routes/actions?query=event%3Arelease+workflow%3ACI)
[![pypi](https://img.shields.io/pypi/v/flask_typed_routes.svg)](https://pypi.python.org/pypi/flask_typed_routes)
[![codecov](https://codecov.io/gh/rmoralespp/jsonl/branch/main/graph/badge.svg)](https://app.codecov.io/gh/rmoralespp/flask_typed_routes)
[![license](https://img.shields.io/github/license/rmoralespp/jsonl.svg)](https://github.com/rmoralespp/flask_typed_routes/blob/main/LICENSE)

## About

**flask_typed_routes** is a `Python` library designed to validate `Flask` requests effortlessly with `Pydantic`.

## Features

- **Type Safety:** Automatically validates request parameters based on type annotations.
- **Easy Integration:** Simple decorator syntax for applying validation to Flask routes.
- **Error Handling:** Automatically returns meaningful error responses for validation failures.

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

Example of a simple Flask application using `flask_typed_routes`:

Create a file `posts.py` with:

```python
import flask
import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/posts/<user>/')
@flask_tpr.typed_route
def read_user_posts(user: str, skip: int = 0, limit: int = 10):
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
flask --app posts run
```

**Data conversion:**

Open your browser and go to [127.0.0.1:5000/posts/myuser/?skip=20](http://127.0.0.1:5000/posts/myuser/?skip=20)
You will see the JSON response as:

```json
{
  "limit": 10,
  "skip": 20,
  "user": "myuser"
}
```

**Data validation:**

Open your browser and go to [127.0.0.1:5000/posts/myuser/?skip=abc](http://127.0.0.1:5000/posts/myuser/?skip=abc)
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

## Documentation

For more detailed information and usage examples, refer to the
project [documentation](https://rmoralespp.github.io/flask_typed_routes/)

## Development

To contribute to the project, you can run the following commands for testing and documentation:

### Running Unit Tests

Install the development dependencies and run the tests:

```
(env)$ pip install -r requirements-dev.txt  # Skip if already installed
(env)$ python -m pytest tests/
(env)$ python -m pytest --cov # Run tests with coverage
```

### Building the Documentation

To build the documentation locally, use the following commands:

```
(env)$ pip install -r requirements-doc.txt # Skip if already installed
(env)$ mkdocs serve # Start live-reloading docs server
(env)$ mkdocs build # Build the documentation site
```

## License

This project is licensed under the [MIT license](LICENSE).