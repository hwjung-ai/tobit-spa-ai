# Tobit SPA AI Agents Documentation

This document outlines various agent capabilities and configurations.

## API Manager

The API Manager allows defining and executing custom APIs. It supports several logic types.

### HTTP Logic Type

The `http` logic type allows you to create custom API endpoints that act as a proxy to external HTTP services.

**Logic Type:** `http`

#### `logic_body` Specification

The `logic_body` for an `http` API must be a JSON object with the following fields:

-   `method` (string, optional): The HTTP method to use. Defaults to `"GET"`. Supported methods are those supported by `httpx` (e.g., `"GET"`, `"POST"`, `"PUT"`, `"DELETE"`).
-   `url` (string, required): The URL of the external endpoint to call.
-   `headers` (object, optional): A key-value map of HTTP headers to send with the request.
-   `params` (object, optional): A key-value map of query string parameters to append to the URL.
-   `body` (object, optional): A JSON object to be sent as the request body for methods like `POST` or `PUT`.

#### Example `logic_body`

Here is an example that fetches a single "todo" item from the JSONPlaceholder test service.

```json
{
  "method": "GET",
  "url": "https://jsonplaceholder.typicode.com/todos/1",
  "headers": {
    "Accept": "application/json"
  },
  "params": {},
  "body": null
}
```

When this API is executed, it will make a `GET` request to the specified URL and return the response from the external service, adapted into the standard API Manager result format.
#### Response structure

The HTTP logic result is normalized into the usual API Manager payload:

`json
{
   api: { ... },