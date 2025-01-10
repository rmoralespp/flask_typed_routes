import flask


class InvalidParameterTypeError(TypeError):
    """Called if the developer supplies a non-standard parameter type"""

    pass


class ValidationError(Exception):
    """Called if pydantic validation fails."""

    def __init__(self, errors):
        self.errors = errors


def handler(error, status_code, /):
    """
    Handle validation errors.

    :param ValidationError error: Validation error instance.
    :param int status_code: Validation error status code to return in the response.
    :return: JSON response with the errors.
    """

    return flask.jsonify({"errors": error.errors}), status_code
