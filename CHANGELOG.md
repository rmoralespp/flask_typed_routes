## Releases

### v0.2.1 (2025-01-29)

- **Breaking-Change**: `FlaskTypedRoutes` fields can't receive the `multi` parameter in the constructor anymore. Now, 
   the fields check if the parameter is a multiple value based on the type annotation (list, set, tuple).
- **Fix**: The `typed_route` decorator can now receive OpenApi reference `parameters` ($ref).
- **Add**: Using `json_schema_extra` param of Pydantic field to add properties extra to the OpenAPI parameter schema.

### v0.2.0 (2025-01-17)

- **Add**: The `FlaskTypedRoutes` class now receives the `openapi_url_prefix` and `openapi_url_json` parameters in 
   the constructor to define the OpenAPI schema URL and Api interactive documentation
- **Breaking-Change**: `FlaskTypedRoutes` can't receive the `exclude_doc_url_prefix` parameter in the constructor anymore.
- **Breaking-Change**: `FlaskTypedRoutes` now hasn't the `openapi_schema ` attribute. The OpenAPI schema is served in the 
   URL defined by `openapi_url_json`.
- **Improvement**: Avoid redundant OpenApi components in the schema.

### v0.1.3 (2025-01-13)

- **Fix**: Exclude validation errors "ctx" because can't be serialized to JSON.
- **Change**: Use OpenApi `default` response if `status_code` is not specified in `typed_route` decorator.

### v0.1.2 (2025-01-10)

- **Change**: Improved the OpenApi schema `summary` and `operationId` of class-based view endpoints.
- **Change**: Register endpoints that do not have type annotations in the OpenApi schema.
- **Add**: `FlaskTypedRoutes` class allows through the `exclude_doc_url_prefix` parameter to exclude from the OpenApi scheme 
   the endpoints associated with the generation of the Interactive documentation.
- **Add**: `FlaskTypedRoutes` class allows through the `validation_error_status_code` parameter to define the status code 
   to be returned when a validation error occurs. The default value is 400.

### v0.1.1 (2025-01-08)

- **Change**: Improved OpenAPI schema to include default HTTP response.

### v0.1.0 (2025-01-07)

- **Add**: Add OpenAPI support to generate the API documentation.
- **Breaking-Change**: `typed_route` decorator now it called with parentheses.
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