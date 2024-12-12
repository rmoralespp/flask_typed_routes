import functools
import urllib.parse

import pydantic

pydantic_url = functools.partial(
    urllib.parse.urljoin, f"https://errors.pydantic.dev/{pydantic.version.version_short()}/v/"
)
