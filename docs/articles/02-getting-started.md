---
title: 'Getting Started with Rift in 5 Minutes'
description: 'From zero to mock server: a hands-on guide to creating your first API mocks.'
audience: [developer]
deployment_mode: [process, container]
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Getting Started with Rift in 5 Minutes

*From zero to mock server: A hands-on guide to creating your first API mocks*

---

In the [previous post](./01-introducing-rift.md), we introduced Rift as a high-performance Mountebank alternative. Now let's get our hands dirty and build something real.

By the end of this post, you'll have:
- A running Rift server
- Multiple mock endpoints
- Understanding of predicates and responses
- Practical examples you can adapt

Let's go!

## Installation Options

### Docker (Recommended)

The fastest way to get started:

```bash
docker pull zainalpour/rift-proxy:latest
docker run -p 2525:2525 -p 4545:4545 zainalpour/rift-proxy:latest
```

### Homebrew (macOS/Linux)

```bash
brew tap achird-labs/rift
brew install rift
rift-http-proxy
```

### npm (Node.js Projects)

```bash
npm install @rift-vs/rift
```

```javascript
import rift from '@rift-vs/rift';

const server = await rift.create({ port: 2525 });
// Your tests here
await server.close();
```

### Cargo (Rust)

```bash
cargo install rift-http-proxy
rift-http-proxy
```

## Understanding the Architecture

Rift has a simple but powerful architecture:

```
┌─────────────────────────────────────────────────┐
│                  Admin API (:2525)               │
│         Create, manage, delete imposters         │
└─────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Imposter    │ │ Imposter    │ │ Imposter    │
│ :4545       │ │ :4546       │ │ :4547       │
│ User API    │ │ Order API   │ │ Auth API    │
└─────────────┘ └─────────────┘ └─────────────┘
```

- **Admin API** (port 2525): REST API to manage imposters
- **Imposters**: Mock servers, each on its own port
- **Stubs**: Request/response pairs within an imposter

## Your First Imposter

Let's create a simple user API mock:

```bash
curl -X POST http://localhost:2525/imposters \
  -H "Content-Type: application/json" \
  -d '{
    "port": 4545,
    "protocol": "http",
    "name": "User Service",
    "stubs": [
      {
        "predicates": [
          { "equals": { "method": "GET", "path": "/users" } }
        ],
        "responses": [
          {
            "is": {
              "statusCode": 200,
              "headers": { "Content-Type": "application/json" },
              "body": [
                { "id": 1, "name": "Alice", "email": "alice@example.com" },
                { "id": 2, "name": "Bob", "email": "bob@example.com" }
              ]
            }
          }
        ]
      }
    ]
  }'
```

Test it:

```bash
curl http://localhost:4545/users
```

Response:
```json
[
  { "id": 1, "name": "Alice", "email": "alice@example.com" },
  { "id": 2, "name": "Bob", "email": "bob@example.com" }
]
```

## Adding More Endpoints

Let's expand our user service with CRUD operations:

```bash
curl -X POST http://localhost:2525/imposters \
  -H "Content-Type: application/json" \
  -d '{
    "port": 4546,
    "protocol": "http",
    "name": "Complete User API",
    "stubs": [
      {
        "predicates": [{ "equals": { "method": "GET", "path": "/users" } }],
        "responses": [{
          "is": {
            "statusCode": 200,
            "headers": { "Content-Type": "application/json" },
            "body": [
              { "id": 1, "name": "Alice" },
              { "id": 2, "name": "Bob" }
            ]
          }
        }]
      },
      {
        "predicates": [
          { "equals": { "method": "GET" } },
          { "matches": { "path": "/users/\\d+" } }
        ],
        "responses": [{
          "is": {
            "statusCode": 200,
            "headers": { "Content-Type": "application/json" },
            "body": { "id": 1, "name": "Alice", "email": "alice@example.com" }
          }
        }]
      },
      {
        "predicates": [
          { "equals": { "method": "POST", "path": "/users" } }
        ],
        "responses": [{
          "is": {
            "statusCode": 201,
            "headers": {
              "Content-Type": "application/json",
              "Location": "/users/3"
            },
            "body": { "id": 3, "name": "New User", "message": "Created" }
          }
        }]
      },
      {
        "predicates": [
          { "equals": { "method": "DELETE" } },
          { "matches": { "path": "/users/\\d+" } }
        ],
        "responses": [{
          "is": { "statusCode": 204 }
        }]
      }
    ]
  }'
```

Test all endpoints:

```bash
# List users
curl http://localhost:4546/users

# Get specific user
curl http://localhost:4546/users/1

# Create user
curl -X POST http://localhost:4546/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie"}'

# Delete user
curl -X DELETE http://localhost:4546/users/1
```

## Using Configuration Files

Instead of curl commands, use JSON files for better maintainability:

**imposters.json:**
```json
{
  "imposters": [
    {
      "port": 4545,
      "protocol": "http",
      "name": "User Service",
      "stubs": [
        {
          "predicates": [{ "equals": { "path": "/health" } }],
          "responses": [{ "is": { "statusCode": 200, "body": "OK" } }]
        },
        {
          "predicates": [{ "equals": { "method": "GET", "path": "/users" } }],
          "responses": [{
            "is": {
              "statusCode": 200,
              "body": [{ "id": 1, "name": "Alice" }]
            }
          }]
        }
      ]
    },
    {
      "port": 4546,
      "protocol": "http",
      "name": "Order Service",
      "stubs": [
        {
          "predicates": [{ "equals": { "method": "GET", "path": "/orders" } }],
          "responses": [{
            "is": {
              "statusCode": 200,
              "body": [{ "id": 101, "userId": 1, "total": 99.99 }]
            }
          }]
        }
      ]
    }
  ]
}
```

Load it:

```bash
# Docker
docker run -p 2525:2525 -p 4545:4545 -p 4546:4546 \
  -v $(pwd)/imposters.json:/imposters.json \
  zainalpour/rift-proxy:latest \
  --configfile /imposters.json

# Binary
rift-http-proxy --configfile imposters.json
```

## Response Cycling

Simulate different responses for the same request:

```json
{
  "stubs": [{
    "predicates": [{ "equals": { "path": "/api/status" } }],
    "responses": [
      { "is": { "statusCode": 200, "body": "Response 1" } },
      { "is": { "statusCode": 200, "body": "Response 2" } },
      { "is": { "statusCode": 503, "body": "Service Unavailable" } }
    ]
  }]
}
```

Each request cycles through responses:
```bash
curl http://localhost:4545/api/status  # Response 1
curl http://localhost:4545/api/status  # Response 2
curl http://localhost:4545/api/status  # Service Unavailable
curl http://localhost:4545/api/status  # Response 1 (cycles back)
```

## Adding Latency

Simulate network delays with the `wait` behavior:

```json
{
  "stubs": [{
    "predicates": [{ "equals": { "path": "/slow" } }],
    "responses": [{
      "is": { "statusCode": 200, "body": "Finally!" },
      "_behaviors": { "wait": 2000 }
    }]
  }]
}
```

This adds a 2-second delay before responding.

## Default Responses

Handle unmatched requests gracefully:

```json
{
  "port": 4545,
  "protocol": "http",
  "defaultResponse": {
    "statusCode": 404,
    "headers": { "Content-Type": "application/json" },
    "body": { "error": "Not Found", "message": "No matching stub" }
  },
  "stubs": [...]
}
```

## Viewing and Managing Imposters

### List All Imposters

```bash
curl http://localhost:2525/imposters
```

### Get Imposter Details

```bash
curl http://localhost:2525/imposters/4545
```

### Delete an Imposter

```bash
curl -X DELETE http://localhost:2525/imposters/4545
```

### Delete All Imposters

```bash
curl -X DELETE http://localhost:2525/imposters
```

## Recording Requests

Enable request recording for debugging:

```json
{
  "port": 4545,
  "protocol": "http",
  "recordRequests": true,
  "stubs": [...]
}
```

View recorded requests:

```bash
curl http://localhost:2525/imposters/4545
```

The response includes a `requests` array with all received requests.

## Node.js Integration Example

For Node.js projects, the npm package provides a clean API:

```javascript
import rift from '@rift-vs/rift';

describe('User API', () => {
  let server;

  beforeAll(async () => {
    server = await rift.create({ port: 2525 });
  });

  afterAll(async () => {
    await server.close();
  });

  beforeEach(async () => {
    await server.deleteAllImposters();
  });

  it('should return users', async () => {
    await server.createImposter({
      port: 4545,
      protocol: 'http',
      stubs: [{
        predicates: [{ equals: { path: '/users' } }],
        responses: [{
          is: {
            statusCode: 200,
            body: [{ id: 1, name: 'Alice' }]
          }
        }]
      }]
    });

    const response = await fetch('http://localhost:4545/users');
    const users = await response.json();

    expect(users).toHaveLength(1);
    expect(users[0].name).toBe('Alice');
  });
});
```

## Quick Reference

| Action | Command |
|--------|---------|
| Start Rift | `docker run -p 2525:2525 zainalpour/rift-proxy:latest` |
| Create imposter | `POST http://localhost:2525/imposters` |
| List imposters | `GET http://localhost:2525/imposters` |
| Get imposter | `GET http://localhost:2525/imposters/:port` |
| Delete imposter | `DELETE http://localhost:2525/imposters/:port` |
| Delete all | `DELETE http://localhost:2525/imposters` |

## What's Next?

You now have the fundamentals of Rift. In the next post, we'll cover **migrating from Mountebank to Rift** — a zero-friction guide for teams already using Mountebank.

**Resources:**
- [GitHub Repository](https://github.com/achird-labs/rift)
- [Documentation](https://achird-labs.github.io/rift/)
- [More Examples](https://github.com/achird-labs/rift/tree/master/examples)

---

*Questions? Found an issue? Open an issue on GitHub or leave a comment below!*

---

**Tags:** #APITesting #MockServer #Tutorial #Rift #ServiceVirtualization #Testing
