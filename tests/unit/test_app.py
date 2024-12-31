import flask_typed_routes.app as ftr_app
import flask_typed_routes.utils as ftr_utils


def test_typed_route():
    def view_func():
        pass

    typed_view_func = ftr_app.typed_route(view_func)
    assert hasattr(typed_view_func, ftr_utils.TYPED_ROUTE_ATTR)
    assert getattr(typed_view_func, ftr_utils.TYPED_ROUTE_ATTR) == ftr_utils.TYPED_ROUTE_VALUE


def test_is_typed_false():
    def view_func():
        pass

    app = ftr_app.FlaskTypedRoutes(mode=ftr_app.Mode.manual)
    assert not app.is_typed(view_func)


def test_is_typed_true_when_auto():
    def view_func():
        pass

    app = ftr_app.FlaskTypedRoutes(mode=ftr_app.Mode.auto)
    assert app.is_typed(view_func)


def test_is_typed_true_when_manual():
    def view_func():
        pass

    typed_view_func = ftr_app.typed_route(view_func)
    app = ftr_app.FlaskTypedRoutes(mode=ftr_app.Mode.manual)
    assert app.is_typed(typed_view_func)
