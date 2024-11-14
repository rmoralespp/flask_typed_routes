import flask


class InvalidParameterTypeError(TypeError):
    """Called if the developer supplies a non-standard parameter type"""

    pass


class ValidationError(Exception):
    """Called if pydantic validation fails."""

    def __init__(self, errors):
        self.errors = errors


def handler(error: ValidationError):
    """Handle validation errors."""

    return flask.jsonify({"errors": error.errors}), 400
