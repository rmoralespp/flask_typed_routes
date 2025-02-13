# Dependencies Injections


## Dependencies in `typed_route` decorator.

In some cases you don't really need the return value of a dependency inside your path operation function.
But you still need it to be executed/solved.

For those cases, you can add a list of dependencies to the `typed_route` decorator.

```python
import flask
import flask_typed_routes as ftr


app = flask.Flask(__name__)


def verify_token():
    print("Verifying token")


def verify_key():
    print("Verifying key")


@app.get("/items/")
@ftr.typed_route(dependencies=[verify_token, verify_key])
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
import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
app_ftr = ftr.FlaskTypedRoutes(app=app)


def get_user_info():
    return {"username": "admin"}


def get_country_info():
    return {"country_name": "foo"}


@app.get("/items/")
@ftr.typed_route()
def read_items(
    user: t.Annotated[dict, ftr.Depends(get_user_info)],
    country: t.Annotated[dict, ftr.Depends(get_country_info)],
):
    result = {"user": user, "country": country}
    return flask.jsonify(result)
```