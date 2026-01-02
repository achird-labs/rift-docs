---
layout: default
title: 'Mastering Request Matching with Rift Predicates'
---

# Mastering Request Matching with Rift Predicates

*From simple path matching to complex JSONPath queries — the complete guide*

---

The power of a mock server lies in its ability to match requests precisely. Match too broadly, and your tests become unreliable. Match too specifically, and maintenance becomes a nightmare.

Rift supports the full range of Mountebank predicates — and executes them up to 247 times faster. Let's explore how to use them effectively.

## Predicate Fundamentals

Every stub has predicates that determine when it matches. Multiple predicates in an array are ANDed together:

```json
{
  "stubs": [{
    "predicates": [
      { "equals": { "method": "POST" } },
      { "equals": { "path": "/users" } }
    ],
    "responses": [...]
  }]
}
```

This matches only POST requests to /users. Both conditions must be true.

## Basic Predicates

### equals — Exact Matching

The most common predicate. Matches exact values:

```json
{
  "predicates": [{
    "equals": {
      "method": "GET",
      "path": "/api/users",
      "query": { "status": "active" }
    }
  }]
}
```

Matches: `GET /api/users?status=active`
Doesn't match: `GET /api/users?status=inactive`

### deepEquals — Structural Matching

For matching JSON bodies exactly:

```json
{
  "predicates": [{
    "deepEquals": {
      "body": {
        "username": "alice",
        "role": "admin"
      }
    }
  }]
}
```

The entire body structure must match — no extra fields allowed.

### contains — Substring Matching

Match when a value contains a substring:

```json
{
  "predicates": [{
    "contains": { "path": "/api/" }
  }]
}
```

Matches: `/api/users`, `/api/orders/123`, `/v1/api/health`

### startsWith and endsWith

```json
{
  "predicates": [{
    "startsWith": { "path": "/api/v2" }
  }]
}
```

```json
{
  "predicates": [{
    "endsWith": { "path": ".json" }
  }]
}
```

### matches — Regular Expressions

For pattern matching:

```json
{
  "predicates": [{
    "matches": { "path": "/users/\\d+" }
  }]
}
```

Matches: `/users/123`, `/users/456789`
Doesn't match: `/users/abc`, `/users/`

**Common patterns:**

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `\\d+` | One or more digits | `123` |
| `[a-zA-Z]+` | Letters only | `hello` |
| `[a-f0-9-]{36}` | UUID format | `550e8400-e29b-41d4-a716-446655440000` |
| `.*` | Anything | (any string) |

### exists — Field Presence

Check if a field exists (or doesn't):

```json
{
  "predicates": [{
    "exists": {
      "headers": {
        "Authorization": true,
        "X-Debug": false
      }
    }
  }]
}
```

Matches requests WITH Authorization header and WITHOUT X-Debug header.

## Advanced: JSONPath Predicates

JSONPath is incredibly powerful for matching JSON request bodies. And in Rift, it's **247x faster** than Mountebank.

### Basic JSONPath

```json
{
  "predicates": [{
    "jsonpath": { "selector": "$.user.name" },
    "equals": { "body": "Alice" }
  }]
}
```

Matches requests where the body contains:
```json
{
  "user": {
    "name": "Alice",
    "email": "alice@example.com"
  }
}
```

### Array Queries

```json
{
  "predicates": [{
    "jsonpath": { "selector": "$.items[0].sku" },
    "equals": { "body": "PROD-001" }
  }]
}
```

### Existence Checks

```json
{
  "predicates": [{
    "jsonpath": { "selector": "$.metadata.version" },
    "exists": { "body": true }
  }]
}
```

### Practical Example: Order Validation

```json
{
  "stubs": [{
    "predicates": [
      { "equals": { "method": "POST", "path": "/orders" } },
      { "jsonpath": { "selector": "$.items" }, "exists": { "body": true } },
      { "jsonpath": { "selector": "$.customer.id" }, "matches": { "body": "\\d+" } }
    ],
    "responses": [{
      "is": {
        "statusCode": 201,
        "body": { "orderId": "ORD-12345", "status": "created" }
      }
    }]
  }]
}
```

This validates:
- POST to /orders
- Body has an `items` array
- Customer ID is numeric

## Advanced: XPath Predicates

For XML/SOAP services:

```json
{
  "predicates": [{
    "xpath": { "selector": "//user/name/text()" },
    "equals": { "body": "Alice" }
  }]
}
```

Matches:
```xml
<request>
  <user>
    <name>Alice</name>
  </user>
</request>
```

### Namespace Handling

```json
{
  "predicates": [{
    "xpath": {
      "selector": "//soap:Body/ns:GetUser/ns:UserId",
      "ns": {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns": "http://example.com/users"
      }
    },
    "equals": { "body": "123" }
  }]
}
```

## Logical Operators

### and — All Must Match

```json
{
  "predicates": [{
    "and": [
      { "equals": { "method": "POST" } },
      { "contains": { "path": "/api/" } },
      { "exists": { "headers": { "Authorization": true } } }
    ]
  }]
}
```

### or — Any Can Match

```json
{
  "predicates": [{
    "or": [
      { "equals": { "path": "/health" } },
      { "equals": { "path": "/healthz" } },
      { "equals": { "path": "/ready" } }
    ]
  }]
}
```

### not — Negation

```json
{
  "predicates": [{
    "not": {
      "equals": { "method": "DELETE" }
    }
  }]
}
```

Matches any method EXCEPT DELETE.

### Complex Combinations

```json
{
  "predicates": [{
    "and": [
      { "equals": { "method": "POST" } },
      {
        "or": [
          { "startsWith": { "path": "/api/v1" } },
          { "startsWith": { "path": "/api/v2" } }
        ]
      },
      {
        "not": {
          "exists": { "headers": { "X-Test-Mode": true } }
        }
      }
    ]
  }]
}
```

This matches:
- POST requests
- To /api/v1/* OR /api/v2/*
- WITHOUT the X-Test-Mode header

## Predicate Options

### caseSensitive

```json
{
  "predicates": [{
    "equals": { "path": "/API/Users" },
    "caseSensitive": false
  }]
}
```

Matches `/api/users`, `/API/USERS`, `/Api/Users`

### except

Exclude part of the match:

```json
{
  "predicates": [{
    "equals": { "path": "/users/123" },
    "except": "123"
  }]
}
```

Useful for matching structure while ignoring dynamic parts.

## Request Fields Reference

| Field | Description | Example |
|-------|-------------|---------|
| `method` | HTTP method | `"GET"`, `"POST"` |
| `path` | URL path | `"/api/users"` |
| `query` | Query parameters | `{ "page": "1" }` |
| `headers` | Request headers | `{ "Content-Type": "application/json" }` |
| `body` | Request body | String or object |

## Best Practices

### 1. Order Stubs from Specific to General

```json
{
  "stubs": [
    {
      "predicates": [{ "equals": { "path": "/users/admin" } }],
      "responses": [{ "is": { "body": "Admin user" } }]
    },
    {
      "predicates": [{ "matches": { "path": "/users/\\d+" } }],
      "responses": [{ "is": { "body": "Regular user" } }]
    },
    {
      "predicates": [{ "startsWith": { "path": "/users" } }],
      "responses": [{ "is": { "body": "User endpoint" } }]
    }
  ]
}
```

Rift evaluates stubs in order. First match wins.

### 2. Use JSONPath for Complex Bodies

Instead of:
```json
{
  "deepEquals": {
    "body": {
      "user": { "name": "Alice" },
      "timestamp": "...",
      "requestId": "..."
    }
  }
}
```

Use:
```json
{
  "jsonpath": { "selector": "$.user.name" },
  "equals": { "body": "Alice" }
}
```

More flexible and maintains tests when body structure changes.

### 3. Combine Predicates Logically

```json
{
  "predicates": [
    { "equals": { "method": "POST" } },
    { "startsWith": { "path": "/api/" } },
    { "jsonpath": { "selector": "$.action" }, "equals": { "body": "create" } }
  ]
}
```

Each predicate is simple; combined they're powerful.

### 4. Use exists for Optional Fields

```json
{
  "stubs": [
    {
      "predicates": [
        { "equals": { "path": "/orders" } },
        { "exists": { "headers": { "X-Priority": true } } }
      ],
      "responses": [{ "is": { "body": "Priority order" } }]
    },
    {
      "predicates": [{ "equals": { "path": "/orders" } }],
      "responses": [{ "is": { "body": "Regular order" } }]
    }
  ]
}
```

## Performance Tips

1. **Simple predicates are fastest**: `equals` > `contains` > `matches` > `jsonpath`
2. **Use Rift for JSONPath-heavy configs**: 247x faster than Mountebank
3. **Avoid overly complex regex**: Simple patterns compile faster
4. **Limit predicate depth**: Deep `and`/`or` nesting adds overhead

## What's Next?

Now that you can match any request, let's add some chaos:

**Next Post**: Chaos Engineering Made Easy — Fault Injection with Rift

---

*What predicate patterns work best for your use cases? Share in the comments!*

---

**Tags:** #APITesting #Predicates #JSONPath #XPath #MockServer #Rift
