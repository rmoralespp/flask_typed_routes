import collections
import dataclasses
import functools

import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_erros
import flask_typed_routes.openapi as ftr_openapi
import flask_typed_routes.utils as ftr_utils


class Mode:
    """Validation mode for typed routes."""

    auto = "auto"
    manual = "manual"


@dataclasses.dataclass(frozen=True)
class OpenAPI:
    """
    OpenAPI specification for typed routes.

    :param dict paths: The available paths and operations for the API.
    :param dict components_schemas: Reusable schema objects that are inferred from Pydantic models.
    """

    paths: dict
    components_schemas: dict[str:dict]


def typed_route(**openapi_kwargs):

    def worker(view_func, /):
        """
        Decorator for marking a route function as typed for request
        validation using type hints.

        :param view_func: Flask view function
        :return: Flask view function
        """

        obj = ftr_openapi.OperationModel(**openapi_kwargs)  # validate the OpenAPI parameters
        setattr(view_func, ftr_utils.TYPED_ROUTE_ATTR, ftr_utils.TYPED_ROUTE_VALUE)
        setattr(view_func, ftr_utils.TYPED_ROUTE_OPENAPI, obj)
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

    def __init__(self, app=None, validation_error_handler=None, ignore_verbs=None, mode=Mode.auto):
        self.error_handler = validation_error_handler
        self.ignore_verbs = ignore_verbs or self.IGNORE_VERBS
        if mode not in (Mode.auto, Mode.manual):
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode

        self.openapi = OpenAPI(paths=collections.defaultdict(dict), components_schemas=dict())

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
        manual = getattr(view_func, ftr_utils.TYPED_ROUTE_ATTR, None) == ftr_utils.TYPED_ROUTE_VALUE
        return self.mode == Mode.auto or manual

    def update_openapi(self, func, rule, endpoint, kwargs):
        methods = kwargs.get("methods", ()) or getattr(func, "methods", ()) or ("GET",)
        endpoint = endpoint or func.__name__
        spec = ftr_openapi.get_route_paths(func, rule, endpoint, methods)
        self.openapi.paths.update(spec["paths"])
        self.openapi.components_schemas.update(spec["components"]["schemas"])
