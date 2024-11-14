# Query parameters

Parameters not included in the "path" are automatically treated as "query" parameters.

```python
import typing as t

import flask

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/posts/')
@flask_tpr.typed_route
def read_posts(needy: str, skip: int = 0, limit: t.Annotated[int, flask_tpr.Query(alias="max", le=100)] = 100):
    data = {
        'needy': needy,
        'skip': skip,
        'limit': limit,
    }
    return flask.jsonify(data)
```

Explanation:

- `needy`: Query parameter that must be included in the request and must be a string.
- `skip`: Query parameter that is optional and must be an integer. If not included, it defaults to 0.
- `limit`: Query parameter that is optional and must be a string. If not included, it defaults to 100. The parameter is
  validated using the library field `Query` with a maximum value of 100. The parameter is also aliased as `max`.

Note: The alias is used to demonstrate how the library can support Pydantic's Field class.

Valid Request: `http://127.0.0.1:5000/posts/?needy=passed&max=20`

```json
{
  "limit": 20,
  "needy": "passed",
  "skip": 0
}
```

**Invalid Requests:**

**Case1** If "needy" is not included in the request: `http://127.0.0.1:5000/posts/`

```json
{
  "errors": [
    {
      "input": {},
      "loc": [
        "query",
        "needy"
      ],
      "msg": "Field required",
      "type": "missing",
      "url": "https://errors.pydantic.dev/2.9/v/missing"
    }
  ]
}
```

**Case2** If "limit" (alias: "max") is greater than 100: `http://127.0.0.1:5000/posts/?needy=passed&max=1000`

```json
{
  "errors": [
    {
      "ctx": {
        "le": 100
      },
      "input": "1000",
      "loc": [
        "query",
        "max"
      ],
      "msg": "Input should be less than or equal to 100",
      "type": "less_than_equal",
      "url": "https://errors.pydantic.dev/2.9/v/less_than_equal"
    }
  ]
}
```