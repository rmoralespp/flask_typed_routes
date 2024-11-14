import flask

import flask_typed_routes as flask_tpr

app = flask.Flask(__name__)
flask_tpr.FlaskTypeRoutes(app)


@app.route('/posts/<user>/')
@flask_tpr.typed_route
def read_user_posts(user: str, skip: int = 0, limit: int = 10):
    # Parameters not included in the "path" are automatically treated as "query" parameters.
    data = {
        'user': user,
        'skip': skip,
        'limit': limit
    }
    return flask.jsonify(data)
