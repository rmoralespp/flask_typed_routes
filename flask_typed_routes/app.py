import functools

import flask_typed_routes.core as core
import flask_typed_routes.errors as errors
import flask_typed_routes.utils as utils


class FlaskTypeRoutes:
    """
    Flask extension for automatically validating Requests with Pydantic
    by decorating route functions.

    :param app: Flask application instance.
    :param Callable validation_error_handler:
        Custom error handler for the "ValidationError" exception,
        by default it uses the default error handler provided by the library.
    """

    IGNORE_VERBS = ("HEAD", "OPTIONS")

    def __init__(self, app=None, validation_error_handler=None, ignore_verbs=None):
        self.error_handler = validation_error_handler
        self.ignore_verbs = ignore_verbs or self.IGNORE_VERBS
        if app:
            self.init_app(app)

    def init_app(self, app, /):
        # Register the error handler for the "ValidationError"
        app.register_error_handler(errors.ValidationError, self.error_handler or errors.handler)
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
            path_args = utils.extract_rule_params(rule)
            if view_func:
                view = utils.class_based_view(view_func)
                if view:  # class-based view
                    verbs = view.methods or ()  # methods defined in the class
                    verbs = (verb for verb in verbs if hasattr(view, verb.lower()))  # implemented methods
                    verbs = frozenset(verbs).difference(self.ignore_verbs)  # ignore some methods
                    if verbs:  # implemented methods
                        for verb in verbs:
                            method = getattr(view, verb.lower())
                            setattr(view, verb.lower(), core.typed_route(method, path_args))
                    else:  # no implemented methods, use the default "dispatch_request"
                        view.dispatch_request = core.typed_route(view.dispatch_request, path_args)
                else:  # function-based view
                    view_func = core.typed_route(view_func, path_args)

            return func(rule, endpoint=endpoint, view_func=view_func, **kwargs)

        return wrapper
