# Path Parameters

You can validate path parameters in your route by adding type hints to the function signature.

!!! warning
    If no type hint is provided, the route parameters are not validated.

```python
import typing as t

import flask
import flask_typed_routes as flask_tpr


app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/items/<user_id>/<country_iso>')
def read_items(user_id: int, country_iso: t.Annotated[str, flask_tpr.Path(max_length=2)]):
    data = {
        'user_id': user_id,
        'country_iso': country_iso,
    }
    return flask.jsonify(data)
```

**Validations:**

- user_id: Must be an integer.
- country_iso: Must be a string with a maximum length of 2 characters. This parameter is validated using the libray
  field `Path`.

**Valid Request:** `http://127.0.0.1:5000/posts/12/ES`

```json
{
  "country_iso": "ES",
  "user_id": 12
}
```

**Bad Request:** If "user_id" is not an integer: `http://127.0.0.1:5000/posts/abc/ES`

```json
{
  "errors": [
    {
      "input": "abc",
      "loc": [
        "path",
        "user_id"
      ],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "type": "int_parsing",
      "url": "https://errors.pydantic.dev/2.9/v/int_parsing"
    }
  ]
}
```

## Custom Validations

Additionally, you can use the `Path` field which allows you to define more complex validations.

The `Path` field is an extension of Pydantic's field, offering powerful validation capabilities.
This flexibility allows you to tailor path parameter validation to your application's specific needs.`

!!! warning
    The `Path` field is not supported aliasing. You must respect the field's name when using it.
