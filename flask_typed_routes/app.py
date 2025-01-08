import functools

import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_erros
import flask_typed_routes.openapi as ftr_openapi
import flask_typed_routes.utils as ftr_utils


class Mode:
    """Validation mode for typed routes."""

    auto = "auto"
    manual = "manual"


def typed_route(status_code=200, **openapi):
    """
    Decorator for marking a route function as typed for request
    validation using type hints.

    :param int status_code: Status code for the success response.
    :param dict openapi: Describe the OpenAPI operation fields in the route.

    Example:
        openapi = {
            "summary": "A short summary of what the operation does.",
            "tags": ["my-tag"],
            "deprecated": False,
        }
        @typed_route(**openapi)
        def my_route():
            pass

    """

    def worker(view_func, /):
        setattr(view_func, ftr_utils.TYPED_ROUTE_ENABLED, True)
        setattr(view_func, ftr_utils.TYPED_ROUTE_OPENAPI, ftr_openapi.get_operation(**openapi))
        setattr(view_func, ftr_utils.TYPED_ROUTE_STATUS_CODE, status_code)
        return view_func

    return worker


class FlaskTypedRoutes:
    """
    Flask extension for automatically validating Requests with Pydantic
    by decorating route functions.

    :param app: Flask application instance.
    :param Callable validation_error_handler:
        Custom error handler for the "ValidationError" exception,
        by default it uses the default error handler provided by the library.
    :param Tuple[str] ignore_verbs: HTTP verbs to ignore.
    :param str mode: Mode of operation, 'auto' or 'manual'. Default is 'auto'.
    """

    IGNORE_VERBS = ("HEAD", "OPTIONS")

    def __init__(
        self,
        app=None,
        validation_error_handler=None,
        ignore_verbs=None,
        mode=Mode.auto,
        **openapi,
    ):
        self.error_handler = validation_error_handler
        self.ignore_verbs = ignore_verbs or self.IGNORE_VERBS
        if mode not in (Mode.auto, Mode.manual):
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode
        self.openapi_schema = ftr_openapi.get_openapi(**openapi)
        if app:
            self.init_app(app)

    def init_app(self, app, /):
        # Register the error handler for the "ValidationError"
        app.register_error_handler(ftr_erros.ValidationError, self.error_handler or ftr_erros.handler)
        # Replace the "add_url_rule" method with a wrapper that adds the "typed_route" decorator
        app.add_url_rule = self.add_url_rule(app.add_url_rule)

    def add_url_rule(self, func, /):
        """
        Decorator for the "add_url_rule" method of the Flask application.
        Applies the "typed_route" decorator to the view functions.

        :param func: Flask "add_url_rule" method
        """

        @functools.wraps(func)
        def wrapper(rule, endpoint=None, view_func=None, **kwargs):
            path_args = ftr_utils.extract_rule_params(rule)
            if view_func:
                view = ftr_utils.class_based_view(view_func)

                if view:  # class-based view
                    verbs = view.methods or ()  # methods defined in the class
                    verbs = (verb for verb in verbs if hasattr(view, verb.lower()))  # implemented methods
                    verbs = frozenset(verbs).difference(self.ignore_verbs)  # ignore some methods

                    if verbs:  # implemented methods
                        for verb in verbs:
                            method = getattr(view, verb.lower())
                            if self.is_typed(method):
                                new_method = ftr_core.route(method, path_args)
                                self.update_openapi(new_method, rule, endpoint, kwargs)
                                setattr(view, verb.lower(), new_method)

                    # no implemented methods, use the default "dispatch_request"
                    elif self.is_typed(view.dispatch_request):
                        new_method = ftr_core.route(view.dispatch_request, path_args)
                        self.update_openapi(new_method, rule, endpoint, kwargs)
                        view.dispatch_request = new_method

                elif self.is_typed(view_func):  # function-based view
                    view_func = ftr_core.route(view_func, path_args)
                    self.update_openapi(view_func, rule, endpoint, kwargs)

            return func(rule, endpoint=endpoint, view_func=view_func, **kwargs)

        return wrapper

    def is_typed(self, view_func, /):
        enabled = getattr(view_func, ftr_utils.TYPED_ROUTE_ENABLED, False)
        return self.mode == Mode.auto or enabled

    def update_openapi(self, func, rule, endpoint, kwargs, /):
        methods = kwargs.get("methods") or getattr(func, "methods", ()) or ("GET",)
        endpoint = endpoint or func.__name__
        spec = ftr_openapi.get_operations(func, rule, endpoint, methods)
        paths = self.openapi_schema["paths"]
        schemas = self.openapi_schema["components"]["schemas"]
        for path, path_spec in spec["paths"].items():
            if path in paths:
                paths[path].update(path_spec)
            else:
                paths[path] = path_spec
        schemas.update(spec["components"]["schemas"])
