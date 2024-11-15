import functools

import flask_typed_routes.errors as errors
import flask_typed_routes.main as main
import flask_typed_routes.utils as utils


class FlaskTypeRoutes:
    """
    Flask extension for automatically validating Requests with Pydantic
    by decorating route functions.

    :param app: Flask application instance
    :param validation_error_handler:
        Custom error handler for the "ValidationError" exception,
        by default it uses the default error handler provided by the library.
    """

    def __init__(self, app=None, validation_error_handler=None):
        self.error_handler = validation_error_handler
        if app:
            self.init_app(app)

    def init_app(self, app):
        # Register the error handler for the "ValidationError"
        app.register_error_handler(errors.ValidationError, self.error_handler or errors.handler)
        # Replace the "add_url_rule" method with a wrapper that adds the "typed_route" decorator
        app.add_url_rule = self.add_url_rule(app.add_url_rule)

    @staticmethod
    def add_url_rule(func):
        @functools.wraps(func)
        def wrapper(rule, endpoint=None, view_func=None, **kwargs):
            path_args = utils.extract_rule_params(rule)

            view_func = main.typed_route(view_func, path_args) if view_func else view_func
            return func(rule, endpoint=endpoint, view_func=view_func, **kwargs)

        return wrapper
