# -*- coding: utf-8 -*-

import functools
import urllib.parse

import pydantic

pydantic_url = functools.partial(
    urllib.parse.urljoin, f"https://errors.pydantic.dev/{pydantic.version.version_short()}/v/",
)


def login_required(func):
    """Decorator to simulate a login required on the view function."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
