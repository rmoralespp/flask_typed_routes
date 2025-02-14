# -*- coding: utf-8 -*-

import functools

import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_erros
import flask_typed_routes.openapi as ftr_openapi
import flask_typed_routes.utils as ftr_utils


class Mode:
    """Validation mode for typed routes."""

    auto = "auto"
    manual = "manual"


def typed_route(*, status_code=None, dependencies=None, **openapi):
    """
    Decorator for marking a route function as typed for request
    validation using type hints.

    :param int status_code: Status code for the success response.
    :param list[Callable] dependencies: List of dependencies for the route.
            Order of the dependencies is important, as they are executed in the order they are defined.
    :param Unpack[dict[str, Any]] openapi: Describe the OpenAPI operation fields in the route.

    Example:
        @typed_route(status_code=200, summary="My summary", tags=["my-tag"], deprecated=False)
        def my_route():
            pass

    """

    def worker(view_func, /):
        setattr(view_func, ftr_utils.ROUTE_ENABLED, True)
        setattr(view_func, ftr_utils.ROUTE_OPENAPI, openapi)
        setattr(view_func, ftr_utils.ROUTE_STATUS_CODE, status_code)
        setattr(view_func, ftr_utils.ROUTE_DEPENDENCIES, dependencies)
        return view_func

    return worker


class FlaskTypedRoutes:
    """
    Flask extension for automatically validating Requests with Pydantic
    by decorating route functions.
    """

    IGNORE_VERBS = ("HEAD", "OPTIONS")

    def __init__(
        self,
        app=None,
        validation_error_handler=None,
        validation_error_status_code=400,
        ignore_verbs=None,
        mode=Mode.auto,
        **openapi,
    ):
        """
        :param app: Flask application instance.
        :param Callable validation_error_handler:
            Custom error handler for the "ValidationError" exception,
            by default, it uses the default error handler provided by the library.
        :param int validation_error_status_code: Status code for the validation error response.
        :param tuple[str, ...] ignore_verbs: HTTP verbs to ignore.
        :param str mode: Mode of operation, 'auto' or 'manual'. Default is 'auto'.
        :param Unpack[dict[str, Any]] openapi: OpenAPI schema definition for the App.
        """

        self.error_handler = validation_error_handler
        self.validation_error_status_code = validation_error_status_code
        self.ignore_verbs = ignore_verbs or self.IGNORE_VERBS

        if mode not in (Mode.auto, Mode.manual):
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode

        self.openapi = ftr_openapi.OpenApi(**openapi)
        self.routes = []  # registered routes
        if app:
            self.init_app(app)

    def default_error_handler(self, error, /):
        return ftr_erros.handler(error, self.validation_error_status_code)

    def init_app(self, app, /):
        # Register the error handler for the "ValidationError"
        app.register_error_handler(ftr_erros.ValidationError, self.error_handler or self.default_error_handler)
        # Replace the "add_url_rule" method with a wrapper that adds the "route" decorator
        app.add_url_rule = self.add_url_rule(app.add_url_rule)

    def add_url_rule(self, func, /):
        """
        Decorator for the "add_url_rule" method of the Flask.
        Applies of a validation decorator to the view functions.

        :param func: Flask "add_url_rule" method
        """

        @functools.wraps(func)
        def wrapper(rule, endpoint=None, view_func=None, **kwargs):
            view_args = ftr_utils.extract_rule_params(rule)
            methods = kwargs.get("methods") or ("GET",)
            if view_func:
                # name of the view function or view class if not endpoint is provided
                view_name = endpoint or view_func.__name__
                view_class = ftr_utils.class_based_view(view_func)
                if view_class:  # class-based view
                    verbs = view_class.methods or ()  # methods defined in the class
                    verbs = (verb for verb in verbs if hasattr(view_class, verb.lower()))  # implemented methods
                    verbs = frozenset(verbs).difference(self.ignore_verbs)  # ignore some methods

                    if verbs:  # implemented methods
                        for verb in verbs:
                            method = getattr(view_class, verb.lower())
                            if self.is_typed(method):
                                new_method = ftr_core.validate(method, view_name, view_args)
                                self.register_route(new_method, rule, view_name, (verb,), view_args)
                                setattr(view_class, verb.lower(), new_method)

                    # no implemented methods, use the default "dispatch_request"
                    elif self.is_typed(view_class.dispatch_request):
                        new_method = ftr_core.validate(view_class.dispatch_request, view_name, view_args)
                        self.register_route(new_method, rule, view_name, methods, view_args)
                        view_class.dispatch_request = new_method

                elif self.is_typed(view_func):  # function-based view
                    view_func = ftr_core.validate(view_func, view_name, view_args)
                    self.register_route(view_func, rule, view_name, methods, view_args)

            return func(rule, endpoint=endpoint, view_func=view_func, **kwargs)

        return wrapper

    def is_typed(self, view_func, /):
        enabled = getattr(view_func, ftr_utils.ROUTE_ENABLED, False)
        return self.mode == Mode.auto or enabled

    def register_route(self, view_func, rule, name, methods, rule_args, /):
        route = ftr_utils.RouteInfo(
            func=view_func,
            rule=rule,
            args=rule_args,
            name=name,
            methods=methods,
        )
        self.routes.append(route)

    def get_openapi_schema(self):
        """
        Get the OpenAPI schema document based on the Flask application routes.

        +ATTENTION+: Use this after registering the routes and blueprints,
        as the FlaskTypedRoutes first needs to collect the routes to have the full data.

        :rtype: dict[str, Any]
        """

        return self.openapi.get_schema(self.routes, self.validation_error_status_code)
