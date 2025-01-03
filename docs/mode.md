## Validation Modes

The library provides two modes of operation for request validation: `auto` and `manual`. These modes determine how
validation is applied to endpoints.

### `auto` Mode (Default)

In `auto` mode, the library automatically validates the requests of all endpoints that have type hints in their function
signatures. This mode simplifies development by eliminating the need for explicit configuration, ensuring that all typed
routes are validated without additional effort.

#### Key Features of `auto` Mode:

- Automatically validates all routes with type hints.
- Minimal configuration required.
- Suitable for most use cases where automatic validation is preferred.

#### Example:

```python
import typing as t

import annotated_types as at
import flask
import flask_typed_routes as ftr

api = flask.Flask(__name__)
ftr.FlaskTypedRoutes(api)  # Default mode is 'auto'


@api.get('/products/<int:product_id>/')
def get_product(pk: t.Annotated[int, at.Gt(10)]):
    # The 'product_id' parameter is automatically validated as an integer.
    return flask.jsonify({"product_id": pk})


@api.get('/orders/<int:order_id>/')
def get_order(order_id: t.Annotated[int, at.Gt(10)]):
    # The 'order_id' parameter is also automatically validated.
    return flask.jsonify({"order_id": order_id})
```

In this example, both `get_product` and `get_order` endpoints automatically validate the incoming parameters based on
their type hints.

---

### `manual` Mode

In `manual` mode, the user explicitly specifies which routes should be validated by applying the `typed_route`
decorator. This mode provides greater control, allowing developers to selectively enable validation only where needed.

#### Key Features of `manual` Mode:

- Validation is applied only to routes with the `typed_route` decorator.
- Offers granular control over validation.
- Useful for advanced use cases where not all routes require validation.

#### How to Enable `manual` Mode:

Set the mode to `manual` when initializing the library:

```python
import typing as t

import annotated_types as at
import flask

import flask_typed_routes as ftr

api = flask.Flask(__name__)
ftr.FlaskTypedRoutes(api, mode=ftr.Mode.manual)


@api.get('/products/<int:pk>/')
@ftr.typed_route()  # Validation is explicitly enabled for this route.
def get_product(pk: t.Annotated[int, at.Gt(10)]):
    # The 'pk' parameter is validated as an integer.
    return flask.jsonify({"pk": pk})


@api.get('/orders/<int:order_id>/')
def get_order(order_id: t.Annotated[int, at.Gt(10)]):
    # The 'order_id' parameter is NOT validated.
    return flask.jsonify({"order_id": order_id})
```

In this example:

- The `get_product` endpoint validates the `pk` parameter because the `typed_route` decorator is applied.
- The `get_order` endpoint does not validate the `order_id` parameter because it lacks the decorator.

---

### Summary

| Mode     | Validation Scope                                | Use Case                           |
|----------|-------------------------------------------------|------------------------------------|
| `auto`   | All endpoints with type hints                   | Default, for seamless validation   |
| `manual` | Only endpoints with `typed_route` decorator     | Advanced, for selective validation |

Choose the mode that best suits your project's needs. For most cases, `auto` mode provides a hassle-free experience,
while `manual` mode allows for precise control over validation behavior.
