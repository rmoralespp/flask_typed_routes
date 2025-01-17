import unittest.mock

import flask_typed_routes.app as ftr_app
import flask_typed_routes.utils as ftr_utils


def test_typed_route():
    openapi = {
        "summary": "summary",
        "tags": ["my-tag"],
        "deprecated": False,
    }
    view_func = unittest.mock.Mock()
    typed_view_func = ftr_app.typed_route(200, **openapi)(view_func)
    assert getattr(typed_view_func, ftr_utils.ROUTE_ENABLED)
    assert getattr(view_func, ftr_utils.ROUTE_OPENAPI, openapi) == openapi
    assert getattr(view_func, ftr_utils.ROUTE_STATUS_CODE) == 200


def test_is_typed_false():
    app = ftr_app.FlaskTypedRoutes(mode=ftr_app.Mode.manual)
    assert not app.is_typed(object())


def test_is_typed_true_when_auto():
    app = ftr_app.FlaskTypedRoutes(mode=ftr_app.Mode.auto)
    assert app.is_typed(object())


def test_is_typed_true_when_manual():
    app = ftr_app.FlaskTypedRoutes(mode=ftr_app.Mode.manual)
    view_func = ftr_app.typed_route()(unittest.mock.Mock())
    assert app.is_typed(view_func)
