## Handling Errors

If you need to change default output for validation errors, you can pass a
custom error handler to `FlaskTypeRoutes` constructor.

```python
import flask
import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)


def custom_error_handler(error):
    return flask.jsonify({"detail": error.errors}), 400


flask_tpr.FlaskTypeRoutes(app, validation_error_handler=custom_error_handler)
```