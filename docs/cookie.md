## Cookie Parameters

You can define cookie parameters in the same way as query parameters, with support for multiple values.

```python
import typing as t

import flask
import flask_typed_routes as flask_tpr


app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/items/')
def get_items(session_id: t.Annotated[str, flask_tpr.Cookie(alias="session-id")] = None):
    data = {
        'session_id': session_id,
    }
    return flask.jsonify(data)
```

!!! note
    The alias is used to demonstrate how the library can support Pydantic's Field class.