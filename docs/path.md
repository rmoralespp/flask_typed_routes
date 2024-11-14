# Path Parameters

This section demonstrates how to use the library to validate and enforce types for path parameters in your
Flask application.

```python
import typing as t

import flask
import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/posts/<user_id>/<country_iso>')
@flask_tpr.typed_route
def read_posts(user_id: int, country_iso: t.Annotated[str, flask_tpr.Path(max_length=2)]):
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

Valid Request: `http://127.0.0.1:5000/posts/12/ES`

```json
{
  "country_iso": "ES",
  "user_id": 12
}
```

**Invalid Requests:**

**Case1** If "user_id" is not an integer: `http://127.0.0.1:5000/posts/abc/ES`

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

**Case2** If "country_iso" is not a string with a maximum length of 2
characters: `http://127.0.0.1:5000/posts/12/ESP`

```
{

      "errors": [
            {
                  "ctx": {
                        "max_length": 2
                  },
                  "input": "ESP",
                  "loc": [
                        "path",
                        "country_iso"
                  ],
                  "msg": "String should have at most 2 characters",
                  "type": "string_too_long",
                  "url": "https://errors.pydantic.dev/2.9/v/string_too_long"
            }
      ]

}
```

**Custom Path Validations**

The `Path` field is an extension of Pydantic's field, offering powerful validation capabilities.
This flexibility allows you to tailor path parameter validation to your application's specific needs.
