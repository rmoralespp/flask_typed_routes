# Request Body

To declare a request body, you use Pydantic models with all their power and benefits
The library provides annotations like `JsonBody()` to validate specific fields in the request body.


Basic Usage of request Body Validation:

```python
import typing as t

import flask
import pydantic

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


class Post(pydantic.BaseModel):
    title: str
    author: str


@app.post('/posts/')
@flask_tpr.typed_route
def create_post(post: Post):
    return flask.jsonify(post.model_dump())


@app.put('/posts/<post_id>/')
@flask_tpr.typed_route
def update_post(
    post_id: int,
    title: t.Annotated[str, flask_tpr.JsonBody()] = None,
    author: t.Annotated[str, flask_tpr.JsonBody()] = None,
):
    data = {
        'post_id': post_id,
        'title': title,
        'author': author,
    }
    return flask.jsonify(data)
```

Explanation:

- `Post`: Pydantic model that represents the structure of the request body. The model has two fields: `title` and
  `author`.
- `create_post`: Route that accepts a POST request with a JSON body that must match the `Post` model.
- `update_post`: Route that accepts a URL parameter `post_id` that must be an integer. The route also accepts two
  optional JSON body parameters: `title` and `author`. The parameters are validated using the library field `JsonBody`.

### Create a new POST

**Invalid request Body:**
`http://127.0.0.1:5000/posts/`

```json
{
  "title": "Hello, World!"
}
```

**Http Response:**

```json
{
  "errors": [
    {
      "input": {
        "title": "Hello, World!"
      },
      "loc": [
        "body",
        "author"
      ],
      "msg": "Field required",
      "type": "missing",
      "url": "https://errors.pydantic.dev/2.9/v/missing"
    }
  ]
}
```

### Update a POST

**Invalid request Body:**
`http://127.0.0.1:5000/posts/123`

```json
{
  "title": 111
}
```

**Http Response:**

```json
{
  "errors": [
    {
      "input": 111,
      "loc": [
        "body",
        "title"
      ],
      "msg": "Input should be a valid string",
      "type": "string_type",
      "url": "https://errors.pydantic.dev/2.9/v/string_type"
    }
  ]
}
```

