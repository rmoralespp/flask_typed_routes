## Header parameters

You can define header parameters in the same way as query/cookie parameters, with support for multiple values.

```python
import typing as t

import flask
import flask_typed_routes as flask_tpr


app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/items/')
def get_items(auth: t.Annotated[str, flask_tpr.Header(alias="Authorization")] = None):
    data = {
        'auth': auth,
    }
    return flask.jsonify(data)
```

!!! note
    The alias is used to demonstrate how the library can support Pydantic's Field class.