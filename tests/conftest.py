import functools
import typing as t

import flask
import flask.views
import pydantic
import pytest

import flask_typed_routes as flask_tpr


def login_required(func):
    """Decorator to simulate a login required on the view function."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class User(pydantic.BaseModel):
    user_id: t.Annotated[int, pydantic.Field(alias="id")]  # Testing alias
    username: str
    password: pydantic.constr(min_length=4)
    full_name: str | None = None


class Product(pydantic.BaseModel):
    product_id: t.Annotated[int, pydantic.Field(alias="id")]  # Testing alias
    name: str
    description: str | None = None
    price: float
    stock: int
    category: str | None = None


class QueryParams(pydantic.BaseModel):
    skip: int = 0
    limit: int = 10
    sort_by: t.Annotated[str, pydantic.Field(alias='order-by')] = 'id'  # Testing alias


@pytest.fixture(scope='package')
def flask_app():
    api = flask.Flask(__name__)
    flask_tpr.FlaskTypeRoutes(api)
    # Blueprint to test the blueprint registration
    bp = flask.Blueprint('bp', __name__, url_prefix='/bp')

    def add_url(*args, **kwargs):
        api.add_url_rule(*args, **kwargs)
        bp.add_url_rule(*args, **kwargs)

    # Simple view functions ============================================================================================
    def func_path_field(category: str, product_id: int):
        return flask.jsonify({"category": category, "product_id": product_id})

    def func_query(
        skip: int = 0,
        limit: int = 10,
        tags: t.Annotated[list[str], flask_tpr.Query(alias="tag", multi=True)] = None,
    ):
        return flask.jsonify({"skip": skip, "limit": limit, "tags": tags})

    def func_header(
        auth: t.Annotated[str, flask_tpr.Header(alias="Authorization")],
        tags: t.Annotated[list[str], flask_tpr.Header(alias="X-Tag", multi=True)] = None,
    ):
        return flask.jsonify({"auth": auth, "tags": tags})

    def func_cookie(
        session_id: t.Annotated[str, flask_tpr.Cookie(alias="session-id")],
        tags: t.Annotated[list[str], flask_tpr.Cookie(alias="tag", multi=True)] = None,
    ):
        return flask.jsonify({"session_id": session_id, "tags": tags})

    def func_body_model(product: Product):
        return flask.jsonify(product.model_dump())

    def func_body_field(
        product_id: t.Annotated[int, flask_tpr.JsonBody(alias='id')],
        name: t.Annotated[str, flask_tpr.JsonBody()],
    ):
        return flask.jsonify({"product_id": product_id, "name": name})

    def func_body_embed(
        product: t.Annotated[Product, flask_tpr.JsonBody(embed=True)],
        user: t.Annotated[User, flask_tpr.JsonBody(embed=True)],
    ):
        return flask.jsonify({"product": product.model_dump(), "user": user.model_dump()})

    def func_all_params(
        category: str,
        product_id: int,
        product: Product,
        skip: int = 0,
        limit: int = 10,
        auth: t.Annotated[str, flask_tpr.Header(alias="Authorization")] = None,
        session_id: t.Annotated[str, flask_tpr.Cookie(alias="session-id")] = None,
    ):
        result = {
            "category": category,
            "product_id": product_id,
            "product": product.model_dump(),
            "skip": skip,
            "limit": limit,
            "auth": auth,
            "session_id": session_id,
        }
        return flask.jsonify(result)

    # Class-based view functions =======================================================================================
    class MethodView(flask.views.MethodView):

        @login_required
        def get(self, category: str, skip: int = 0, limit: int = 10):
            return flask.jsonify({"category": category, "skip": skip, "limit": limit})

        @login_required
        def post(self, category, product: Product):
            return flask.jsonify({"category": category, "product": product.model_dump()})

    class View(flask.views.View):

        @login_required
        def dispatch_request(self, category: str, skip: int = 0, limit: int = 10):
            return flask.jsonify({"category": category, "skip": skip, "limit": limit})

    # Registering view functions ==================================================================================
    add_url('/products/path/<string:category>/<product_id>/', view_func=func_path_field)
    add_url('/products/query/', view_func=func_query)
    add_url('/products/header/', view_func=func_header)
    add_url('/products/cookie/', view_func=func_cookie)
    add_url('/products/body/model/', view_func=func_body_model, methods=['POST'])
    add_url('/products/body/field/', view_func=func_body_field, methods=['POST'])
    add_url('/products/body/embed/', view_func=func_body_embed, methods=['POST'])
    add_url('/products/all/<string:category>/<product_id>/', view_func=func_all_params, methods=['POST'])

    # Registering class-based views
    api.add_url_rule('/method_views/products/<category>/', view_func=MethodView.as_view('products_method_views'))
    api.add_url_rule('/views/products/<category>/', view_func=View.as_view('products_views'))

    # Registering blueprint routes =====================================================================================
    api.register_blueprint(bp)
    return api


@pytest.fixture(scope='package')
def client(flask_app):
    return flask_app.test_client()
