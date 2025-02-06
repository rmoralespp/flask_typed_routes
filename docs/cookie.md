## Cookie Parameters

You can define cookie parameters in the same way as **query parameters**, with support for multiple
values and validation using Pydantic models.

```python
import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)

SessionId = t.Annotated[str, ftr.Cookie(alias="session-id")]


@app.route('/items/')
def get_items(session_id: SessionId = None):
    data = {
        'session_id': session_id,
    }
    return flask.jsonify(data)
```

## Multiple Cookie Parameters

!!! note
    `Cookie` fields always use the `form` style. An optional `explode` keyword controls the array and object serialization.
