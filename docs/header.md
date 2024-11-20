## Header parameters

You can define header parameters in the same way as **query/cookie parameters**, with support for multiple
values and validation using Pydantic models.

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
