# Path Parameters

You can validate **Path parameters** in your route by adding standard type hints to the function signature.

!!! warning
    If no type hint is provided, the **Path parameters** are not validated.

```python
import typing as t
import flask
import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypedRoutes(app)


@app.route('/items/<category_id>/<lang>/')
def read_items(category_id: int, lang: t.Literal['es', 'en']):
    data = {'category_id': category_id, 'lang': lang}
    return flask.jsonify(data)
```

**Conversion:** The library automatically converts path parameters to their specified types:

- `category_id` is converted to an integer, so your function receives it as an integer.
- `lang` is treated as a string, so your function receives it as a string.

**Validation:**

- `category_id` Must be an integer.
- `lang` Must be either 'es' or 'en'.

**Example request:** `GET http://127.0.0.1:5000/items/12/es`

```json
{
  "category_id": 12,
  "lang": "es"
}
```

**Bad request example:** If `category_id` is not an integer `GET http://127.0.0.1:5000/items/abc/es`

```json
{
  "errors": [
    {
      "input": "abc",
      "loc": [
        "path",
        "category_id"
      ],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "type": "int_parsing",
      "url": "https://errors.pydantic.dev/2.9/v/int_parsing"
    }
  ]
}
```

## Additional validations

You can use the `Path` field with Python's standard `Annotated` field to enforce additional validations on your route
parameters, enabling more complex rules.

The `Path` field is an extension of Pydantic's field, offering powerful validation capabilities.
This flexibility allows you to tailor path parameter validation to your application's specific needs.

!!! warning
    The `Path` field is not supported aliasing. You must respect the **path name** when using it.

```python
import typing as t

import flask
import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypedRoutes(app)


@app.route('/items/<category_id>/')
def read_items(category_id: t.Annotated[int, flask_tpr.Path(ge=1, le=100)]):
    data = {'category_id': category_id}
    return flask.jsonify(data)
```

**Validation:**

- `category_id` must be an integer between 1 and 100.

