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