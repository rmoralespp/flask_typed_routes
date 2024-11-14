import flask_typed_routes.errors
import flask_typed_routes.main


class FlaskTypeRoutes:
    """
    Flask extension that provides a decorator for validating requests
    in typed Flask routes using Pydantic models.

    Features:
    - Type Safety: Automatically validates requests based on type annotations.
    - Easy Integration: Simple decorator syntax for applying validation to Flask routes.
    - Error Handling: Automatically returns meaningful error responses for validation failures.

    :param app: Flask application instance
    :param validation_error_handler:
        Custom error handler for the "ValidationError" exception,
        by default it uses the default error handler provided by the library.
    """

    def __init__(self, app=None, validation_error_handler=None):
        self.error_handler = validation_error_handler
        self.typed_route = flask_typed_routes.main.typed_route  # Shortcut to the "typed_route" decorator

        if app:
            self.init_app(app)

    def init_app(self, app):
        # Register the error handler for the "ValidationError"
        app.register_error_handler(flask_typed_routes.errors.ValidationError, self.error_handler or flask_typed_routes.errors.handler)
