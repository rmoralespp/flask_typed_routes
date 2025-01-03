## Releases

- **Change**: Update the CI trigger to avoid runs on opened pull-request.

### v0.0.8 (2024-12-12)

- **Add**: Supports automatic validation for all routes and manual validation for specific routes using decorators.
- **Change**: The fields provided are now stricter. If is passed an invalid arg, a `InvalidParameterTypeError` will be raised.

### v0.0.7 (2024-12-09)

- **Change**: Use `inspect.get_annotations()` to get function annotations instead of `func.__annotations__`. Python 
  documentation recommends calling this function.
- **Change**: Internal refactor to improve code.

### v0.0.6 (2024-12-05)

- **Fix**: Fix deployment issue with the package.

### v0.0.5 (2024-12-05)

- **Change**: Refactored codebase to improve readability and maintainability.
- **Change**: Add support for Pydantic custom types.
- **Breaking-Change**: Renamed `JsonBody` field to `Body`.

### v0.0.4 (2024-12-03)

- **Change**: Simplified the `typed_route` decorator.
- **Breaking-Change**: Updated the application class name, now it is `FlaskTypedRoutes`.
- **Change**: Respect pydantic-field default defined, even if func-param default is empty.

### v0.0.3 (2024-11-22)

- **Fix**: Resolved an issue with forward annotations during route definition.
- **Add**: Cosmetic improvements to the codebase.

### v0.0.2 (2024-11-20)

- **Fix**: Corrected validation behavior for empty parameters.
- **Add**: Expanded acceptance test coverage.
- **Improve**: Enhanced documentation and usage examples.