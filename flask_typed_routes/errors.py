import flask


class InvalidParameterTypeError(TypeError):
    """Called if the developer supplies a non-standard parameter type"""

    pass


class ValidationError(Exception):
    """Called if pydantic validation fails."""

    def __init__(self, errors):
        self.errors = errors


def handler(error, /):
    """
    Handle validation errors.

    :param ValidationError error: Validation error instance.
    :param ValidationError error: Validation error instance.
    :return: JSON response with the errors.
    """

    return flask.jsonify({"errors": error.errors}), 400
