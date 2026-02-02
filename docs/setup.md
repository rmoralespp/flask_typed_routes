# App Setup

To set up the application, you need to create a new instance of the `Flask` 
application and initialize the `FlaskTypedRoutes` extension with the `app` instance.

!!! note
    The `FlaskTypedRoutes` class must be initialized before registering the **Flask** routes and blueprints 
    to allow the extension to collect the routes and be able to validate the endpoints.

## Basic setup

```python
# -*- coding: utf-8 -*-

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app=app)


@app.get("/")
def read_root():
    return flask.jsonify({"Hello": "World"})
```

## Two-step setup

You can also use the `init_app` method to initialize the extension with the `Flask` application instance in a 
separate step as shown below.

```python
# -*- coding: utf-8 -*-

import flask
import flask_typed_routes as ftr

app_ftr = ftr.FlaskTypedRoutes()

app = flask.Flask(__name__)
app_ftr.init_app(app)

@app.get("/")
def read_root():
    return flask.jsonify({"Hello": "World"})
```