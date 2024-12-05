## Releases

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