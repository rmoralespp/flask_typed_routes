import functools
import uuid

import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_erros
import flask_typed_routes.utils as ftr_utils

# Constants for marking a route function as typed for request validation
_TYPED_ROUTE_ATTR = f"__flask_typed_routes_{uuid.uuid4()}__"
_TYPED_ROUTE_VALUE = object()


class Mode:
    """Validation mode for typed routes."""

    auto = "auto"
    manual = "manual"


def typed_route(view_func, /):
    """
    Decorator for marking a route function as typed for request
    validation using type hints.

    :param view_func: Flask view function
    :return: Flask view function
    """

    setattr(view_func, _TYPED_ROUTE_ATTR, _TYPED_ROUTE_VALUE)
    return view_func


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

    def __init__(self, app=None, validation_error_handler=None, ignore_verbs=None, mode=Mode.auto):
        self.error_handler = validation_error_handler
        self.ignore_verbs = ignore_verbs or self.IGNORE_VERBS
        if mode not in (Mode.auto, Mode.manual):
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode
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
                                setattr(view, verb.lower(), ftr_core.route(method, path_args))

                    # no implemented methods, use the default "dispatch_request"
                    elif self.is_typed(view.dispatch_request):
                        view.dispatch_request = ftr_core.route(view.dispatch_request, path_args)

                elif self.is_typed(view_func):  # function-based view
                    view_func = ftr_core.route(view_func, path_args)

            return func(rule, endpoint=endpoint, view_func=view_func, **kwargs)

        return wrapper

    def is_typed(self, view_func, /):
        return self.mode == Mode.auto or getattr(view_func, _TYPED_ROUTE_ATTR, None) == _TYPED_ROUTE_VALUE
