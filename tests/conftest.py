import functools
import typing as t
import urllib.parse

import annotated_types as at
import flask
import flask.views
import pydantic
import pytest

import flask_typed_routes as ftr

pydantic_url = functools.partial(
    urllib.parse.urljoin, f"https://errors.pydantic.dev/{pydantic.version.version_short()}/v/"
)


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

    @pydantic.computed_field()
    @property
    def extra_field(self) -> str:
        return "Extra field"


@pytest.fixture(scope='package')
def flask_app_auto():
    api = flask.Flask(__name__)
    ftr.FlaskTypedRoutes(api)
    # Blueprint to test the blueprint registration
    bp = flask.Blueprint('bp', __name__, url_prefix='/bp')

    def add_url(*args, **kwargs):
        api.add_url_rule(*args, **kwargs)
        bp.add_url_rule(*args, **kwargs)

    def non_typed_view(pk):
        return flask.jsonify({"pk": pk})

    # Simple view functions ============================================================================================
    def func_path_field(category: str, product_id: t.Annotated[int, at.Gt(5), at.Lt(100)]):
        return flask.jsonify({"category": category, "product_id": product_id})

    def func_query(
        status1: t.Annotated[str, ftr.Query(default='active')],  # Testing default value for query parameter
        status2: str = 'active',  # Testing default value for query parameter
        skip: int = 0,
        limit: pydantic.NonNegativeInt = 10,
        tags: t.Annotated[list[str], ftr.Query(alias="tag")] = None,
    ):
        return flask.jsonify(
            {
                "skip": skip,
                "limit": limit,
                "tags": tags,
                "status1": status1,
                "status2": status2,
            }
        )

    def func_query_model(query: t.Annotated[QueryParams, ftr.Query()]):
        return flask.jsonify(query.model_dump())

    def func_header(
        auth: t.Annotated[str, ftr.Header(alias="Authorization", pattern=r"Bearer \w+")] = None,
        tags: t.Annotated[list[str], ftr.Header(alias="X-Tag")] = None,
    ):
        return flask.jsonify({"auth": auth, "tags": tags})

    def func_cookie(
        session_id: t.Annotated[str, ftr.Cookie(alias="session-id", max_length=4)] = None,
        tags: t.Annotated[list[str], ftr.Cookie(alias="tag")] = None,
    ):
        return flask.jsonify({"session_id": session_id, "tags": tags})

    def func_body_model(product: Product):
        return flask.jsonify(product.model_dump())

    def func_body_field(
        product_id: t.Annotated[int, ftr.Body(alias='id')],
        name: t.Annotated[str, ftr.Body()],
    ):
        return flask.jsonify({"product_id": product_id, "name": name})

    def func_body_embed(
        product: t.Annotated[Product, ftr.Body(embed=True)],
        user: t.Annotated[User, ftr.Body(embed=True)],
    ):
        return flask.jsonify({"product": product.model_dump(), "user": user.model_dump()})

    def test_body_forward_refs(order: 'ForwardRefModel'):
        return flask.jsonify(order.model_dump())

    def func_all_params(
        category: str,
        product_id: int,
        product: Product,
        skip: int = 0,
        limit: int = 10,
        auth: t.Annotated[str, ftr.Header(alias="Authorization")] = None,
        session_id: t.Annotated[str, ftr.Cookie(alias="session-id")] = None,
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

    def func_mixed_annotations(
        category: t.Annotated[
            str,
            at.MinLen(9),  # Testing annotated_types
            pydantic.StringConstraints(max_length=10),  # Testing pydantic strict types
            pydantic.Field(alias='cat', max_length=11),  # Testing override max_length
            pydantic.StringConstraints(pattern=r"\d{10}"),  # Testing a pattern
        ],
    ):
        return flask.jsonify({"category": category})

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
    add_url('/products/<int:pk>/', view_func=non_typed_view)
    add_url('/products/path/<string:category>/<product_id>/', view_func=func_path_field)
    add_url('/products/query/', view_func=func_query)
    add_url('/products/query/model/', view_func=func_query_model)
    add_url('/products/header/', view_func=func_header)
    add_url('/products/cookie/', view_func=func_cookie)
    add_url('/products/body/model/', view_func=func_body_model, methods=['POST'])
    add_url('/products/body/field/', view_func=func_body_field, methods=['POST'])
    add_url('/products/body/embed/', view_func=func_body_embed, methods=['POST'])
    add_url('/products/body/forward-refs/', view_func=test_body_forward_refs, methods=['POST'])
    add_url('/products/all/<string:category>/<product_id>/', view_func=func_all_params, methods=['POST'])
    add_url('/products/mixed/', view_func=func_mixed_annotations)

    # Registering class-based views
    api.add_url_rule('/method_views/products/<category>/', view_func=MethodView.as_view('products_method_views'))
    api.add_url_rule('/views/products/<category>/', view_func=View.as_view('products_views'))

    # Registering blueprint routes =====================================================================================
    api.register_blueprint(bp)
    return api


@pytest.fixture(scope='package')
def flask_app_manual():
    api = flask.Flask(__name__)
    ftr.FlaskTypedRoutes(api, mode=ftr.Mode.manual)

    @api.get('/products/validate/<int:pk>/')
    @ftr.typed_route()
    @login_required
    def get_product_validate(pk: t.Annotated[int, at.Gt(5), at.Lt(100)]):
        return flask.jsonify({"pk": pk})

    @api.get('/products/no-validate/<int:pk>/')
    def get_product_no_validate(pk: t.Annotated[int, at.Gt(5), at.Lt(100)]):
        return flask.jsonify({"product_id": pk})

    return api


@pytest.fixture(scope='package')
def client_auto(flask_app_auto):
    return flask_app_auto.test_client()


@pytest.fixture(scope='package')
def client_manual(flask_app_manual):
    return flask_app_manual.test_client()


# Forward reference Model for testing


class ForwardRefModel(pydantic.BaseModel):
    pk: int
    related: 'ForwardRefModel | None'
