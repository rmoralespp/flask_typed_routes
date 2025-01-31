## Header parameters

You can define header parameters in the same way as **query/cookie parameters**, with support for multiple
values and validation using Pydantic models.

```python
import typing as t

import flask
import flask_typed_routes as ftr

app = flask.Flask(__name__)
ftr.FlaskTypedRoutes(app)


@app.route('/items/')
def get_items(auth: t.Annotated[str, ftr.Header(alias="Authorization")] = None):
    data = {
        'auth': auth,
    }
    return flask.jsonify(data)
```

## Multiple Header Parameters

!!! note
    `Header` fields always use the `simple` style, that is, **comma-separated** values.
