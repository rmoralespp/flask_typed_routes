# Dependencies Injections


## Dependencies in `typed_route` decorator.

In some cases you don't really need the return value of a dependency inside your path operation function.
But you still need it to be executed/solved.

For those cases, you can add a list of dependencies to the `typed_route` decorator.
It should be a list of `Depends()`:

```python
# -*- coding: utf-8 -*-

import flask
import flask_typed_routes as ftr


app = flask.Flask(__name__)


def verify_token():
    print("Verifying token")


def verify_key():
    print("Verifying key")


@app.get("/items/")
@ftr.typed_route(dependencies=[ftr.Depends(verify_token), ftr.Depends(verify_key)])
def read_items():
    return [{"item": "Foo"}, {"item": "Bar"}]
```

## Dependencies using `Depends`

You can use `Depends` field to declare dependencies in your path operation function when you need to use 
the return value of a dependency within that function.

The `Depends` field takes a callable that returns the dependency value.

!!! tip
    The `Depends` can take `use_cache` parameter to cache the dependency value.

```python
# -*- coding: utf-8 -*-

import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
app_ftr = ftr.FlaskTypedRoutes(app=app)


def verify_token():
    return {"token": "value"}


def verify_key():
    return {"key": "value"}



@app.get("/items/")
@ftr.typed_route()
def read_items(
    token: t.Annotated[dict, ftr.Depends(verify_token)],
    key: t.Annotated[dict, ftr.Depends(verify_key)],
):
    result = {"token": token, "key": key}
    return flask.jsonify(result)
```

## Caching Dependencies

By default, `use_cache` is set to `False` so that the dependency is called again (if declared more than once) 
in the same request.

Set `use_cache` to `False` so that after a dependency is called for the first time in a request, if the dependency 
is declared again for the rest of the request (for example, if multiple dependencies need the dependency), 
the value will be reused for the rest of the request.

Example:

```python
# -*- coding: utf-8 -*-

import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
app_ftr = ftr.FlaskTypedRoutes(app=app)


def verify_token():
    return {"token": "value"}

def verify_key():
    return {"token": "value"}


@app.get("/items/")
@ftr.typed_route(dependencies=[ftr.Depends(verify_key, use_cache=True)])
def read_items(token: t.Annotated[dict, ftr.Depends(verify_token, use_cache=True)]):
    return flask.jsonify({"token": token})
```