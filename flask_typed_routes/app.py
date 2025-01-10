import functools

import flask_typed_routes.core as ftr_core
import flask_typed_routes.errors as ftr_erros
import flask_typed_routes.openapi as ftr_openapi
import flask_typed_routes.utils as ftr_utils


class Mode:
    """Validation mode for typed routes."""

    auto = "auto"
    manual = "manual"


def typed_route(status_code=None, **openapi):
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
    :param int validation_error_status_code: Status code for the validation error response.
    :param Tuple[str] ignore_verbs: HTTP verbs to ignore.
    :param str mode: Mode of operation, 'auto' or 'manual'. Default is 'auto'.
    :param str exclude_doc_url_prefix: Exclude the OpenAPI documentation URL prefix.
    :param dict openapi: OpenAPI schema definition for the application.
    """

    IGNORE_VERBS = ("HEAD", "OPTIONS")

    def __init__(
        self,
        app=None,
        validation_error_handler=None,
        validation_error_status_code=400,
        ignore_verbs=None,
        mode=Mode.auto,
        exclude_doc_url_prefix=None,
        **openapi,
    ):
        self.error_handler = validation_error_handler
        self.ignore_verbs = ignore_verbs or self.IGNORE_VERBS
        if mode not in (Mode.auto, Mode.manual):
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode
        self.api_doc_prefix = exclude_doc_url_prefix
        self.validation_error_status_code = validation_error_status_code
        self.openapi_schema = ftr_openapi.get_openapi(**openapi)
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
        Decorator for the "add_url_rule" method of the Flask application.
        Applies the "typed_route" decorator to the view functions.

        :param func: Flask "add_url_rule" method
        """

        @functools.wraps(func)
        def wrapper(rule, endpoint=None, view_func=None, **kwargs):
            path_args = ftr_utils.extract_rule_params(rule)
            is_apidoc = self.api_doc_prefix and rule.startswith(self.api_doc_prefix)
            if view_func and not is_apidoc:
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
                                new_method = ftr_core.route(method, path_args)
                                new_kwargs = {**kwargs, "methods": [verb]}
                                self.register_openapi_route(new_method, rule, view_name, new_kwargs, path_args)
                                setattr(view_class, verb.lower(), new_method)

                    # no implemented methods, use the default "dispatch_request"
                    elif self.is_typed(view_class.dispatch_request):
                        new_method = ftr_core.route(view_class.dispatch_request, path_args)
                        self.register_openapi_route(new_method, rule, view_name, kwargs, path_args)
                        view_class.dispatch_request = new_method

                elif self.is_typed(view_func):  # function-based view
                    view_func = ftr_core.route(view_func, path_args)
                    self.register_openapi_route(view_func, rule, view_name, kwargs, path_args)

            return func(rule, endpoint=endpoint, view_func=view_func, **kwargs)

        return wrapper

    def is_typed(self, view_func, /):
        enabled = getattr(view_func, ftr_utils.TYPED_ROUTE_ENABLED, False)
        return self.mode == Mode.auto or enabled

    def register_openapi_route(self, func, rule, func_name, kwargs, path_args, /):
        methods = kwargs.get("methods") or ("GET",)
        spec = ftr_openapi.get_operations(func, rule, func_name, methods, path_args, self.validation_error_status_code)
        self.register_openapi_paths(spec["paths"])
        self.register_openapi_schemas(spec["components"]["schemas"])

    def register_openapi_paths(self, paths, /):
        current = self.openapi_schema["paths"]
        for path, spec in paths.items():
            current[path].update(spec)

    def register_openapi_schemas(self, schemas, /):
        merged = self.openapi_schema["components"]["schemas"]
        for name, schema in schemas.items():
            matches = (mg_name for mg_name, mg_schema in merged.items() if mg_schema == schema)
            mg_name = next(matches, None)
            if mg_name:
                merged[name] = {"$ref": f"{ftr_openapi.REF_PREFIX}{mg_name}"}
            else:
                merged[name] = schema
