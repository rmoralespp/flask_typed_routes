import typing

import flask
import pydantic
import pytest

import src


class Params(pydantic.BaseModel):
    limit: int = pydantic.Field(gt=0, le=100)
    offset: int = pydantic.Field(0, ge=0)
    order_by: typing.Literal["created_at", "updated_at"] = "created_at"


class Item(pydantic.BaseModel):
    item_id: str
    description: str = None
    country: pydantic.constr(max_length=2)
    price: float


@pytest.fixture(scope='package')
def flask_app():
    def handle_errors(e):
        return flask.jsonify({"errors": e.errors}), 400

    api = flask.Flask(__name__)
    api.register_error_handler(src.RequestValidationError, handle_errors)

    @api.get('/items/')
    @src.typed_route
    def read_items(params: typing.Annotated[Params, src.Query()]):
        return flask.jsonify(params.model_dump())

    @api.get('/items/<item_id>/')
    @src.typed_route
    def read_item(item_id: int):
        data = {"item_id": item_id}
        return flask.jsonify(data)

    @api.get('/user/items/<username>/')
    @src.typed_route
    def read_user_items(
        username: str,
        needy: str,
        skip: int = 0,
        limit: int = 10,
        extra: typing.Annotated[str, src.Query(alias="EXTRA", max_length=2)] = None,
        tags: typing.Annotated[list[str], src.Query(alias="tag", multi=True)] = (),
    ):
        data = {
            "username": username,
            "needy": needy,
            "skip": skip,
            "limit": limit,
            "extra": extra,
            "tags": tags,
        }
        return flask.jsonify(data)

    @api.post('/items/')
    @src.typed_route
    def create_item_from_model(item: Item):
        return flask.jsonify(item.model_dump()), 201

    @api.post('/user/')
    @src.typed_route
    def create_user_from_fields(
        username: typing.Annotated[str, src.JsonBody()],
        full_name: typing.Annotated[str, src.JsonBody()] = None,
    ):
        data = {"username": username, "full_name": full_name}
        return flask.jsonify(data), 201

    return api


@pytest.fixture(scope='package')
def client(flask_app):
    return flask_app.test_client()
