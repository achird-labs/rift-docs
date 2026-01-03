---
layout: default
title: 'Introducing Rift: High-Performance API Mocking for Modern Development'
---

# Introducing Rift: High-Performance API Mocking for Modern Development

*A blazing-fast mock server for testing microservices, simulating APIs, and chaos engineering*

---

Modern software doesn't exist in isolation. Your application talks to payment processors, authentication services, third-party APIs, databases, and dozens of internal microservices. Testing all these interactions is one of the hardest problems in software development.

**Rift** is a high-performance mock server that lets you simulate any HTTP service, inject faults, and test how your application behaves when dependencies fail — all without touching production systems.

## The Problem: Testing Distributed Systems is Hard

Consider a typical e-commerce application:

```
Your App → Payment API → Bank
        → Inventory Service → Database
        → Shipping API → Carrier
        → Email Service → SMTP
```

How do you test what happens when:
- The payment API times out?
- The inventory service returns an error?
- The shipping API is slow?
- The email service is down?

You have three options:

1. **Use real services** — Expensive, slow, unreliable, and potentially dangerous (accidentally charging real cards?)
2. **Build custom mocks** — Time-consuming and hard to maintain
3. **Use a mock server** — Configure responses without writing code

Rift is option 3, done right.

## What Rift Does

Rift creates **imposters** — fake HTTP services that respond exactly how you configure them:

```bash
# Start Rift
docker run -p 2525:2525 -p 4545:4545 ghcr.io/etacassiopeia/rift-proxy:latest

# Create a mock payment API
curl -X POST http://localhost:2525/imposters -H "Content-Type: application/json" -d '{
  "port": 4545,
  "protocol": "http",
  "stubs": [{
    "predicates": [{ "equals": { "path": "/charge", "method": "POST" } }],
    "responses": [{ "is": { "statusCode": 200, "body": "{\"status\": \"approved\", \"transactionId\": \"txn_123\"}" } }]
  }]
}'

# Now your app can call http://localhost:4545/charge instead of the real payment API
curl -X POST http://localhost:4545/charge
# Returns: {"status": "approved", "transactionId": "txn_123"}
```

Point your application at `localhost:4545` instead of the real payment API, and you have a fully controlled test environment.

## Why Rift?

### 1. Blazing Fast Performance

Rift is written in Rust, delivering exceptional throughput:

| Scenario | Requests/Second |
|:---------|:----------------|
| Simple matching | 39,000 RPS |
| JSON body matching | 26,500 RPS |
| XML/XPath matching | 28,700 RPS |
| Complex predicates | 29,300 RPS |

This means your test suite runs faster, your CI/CD pipelines complete sooner, and your cloud bills shrink.

### 2. Powerful Request Matching

Match requests by any combination of:

- **Path and method**: `/api/users` with `GET`
- **Headers**: `Authorization: Bearer token123`
- **Query parameters**: `?status=active&limit=10`
- **JSON body**: Match specific fields with JSONPath
- **XML body**: Match elements with XPath
- **Regular expressions**: Pattern matching on any field

```json
{
  "predicates": [{
    "equals": { "method": "POST", "path": "/api/orders" },
    "jsonpath": { "selector": "$.items[0].sku" },
    "equals": { "body": "PROD-001" }
  }]
}
```

### 3. Native Fault Injection

Test resilience without writing code. Inject latency, errors, and failures declaratively:

```json
{
  "responses": [{
    "is": { "statusCode": 200, "body": "OK" },
    "_rift": {
      "fault": {
        "latency": { "probability": 0.3, "minMs": 100, "maxMs": 500 },
        "error": { "probability": 0.1, "status": 503 }
      }
    }
  }]
}
```

This response will:
- Add 100-500ms latency 30% of the time
- Return a 503 error 10% of the time

Perfect for chaos engineering and resilience testing.

### 4. Stateful Mocking

Real APIs have state. A user logs in, adds items to cart, then checks out. Rift supports stateful scenarios:

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "let count = flow.get('request_count') + 1; flow.set('request_count', count); #{ statusCode: 200, body: `Request #${count}` }"
    }
  }
}
```

Each request increments a counter. Build authentication flows, shopping carts, rate limiters, and more.

### 5. Multi-Language Scripting

When declarative configuration isn't enough, write dynamic responses in your preferred language:

- **Rhai** (built-in, sandboxed) — Safe and fast
- **Lua** — Familiar to many developers
- **JavaScript** — Maximum flexibility

### 6. Record and Replay

Don't want to configure mocks manually? Record real traffic and replay it:

```json
{
  "stubs": [{
    "responses": [{
      "proxy": {
        "to": "https://api.example.com",
        "mode": "proxyAlways",
        "predicateGenerators": [{ "matches": { "path": true, "method": true } }]
      }
    }]
  }]
}
```

Rift records all responses, which you can export and replay later without hitting the real API.

## Mountebank Compatibility

If you're already using [Mountebank](http://www.mbtest.org/), Rift is a drop-in replacement. Same API, same configuration format, just faster:

```bash
# Replace this
docker run -p 2525:2525 mountebank/mountebank

# With this
docker run -p 2525:2525 ghcr.io/etacassiopeia/rift-proxy:latest
```

Your existing `imposters.json` files work unchanged. Rift implements the complete Mountebank API, so your test code doesn't need modifications.

Benchmarks show Rift is **20-250x faster** than Mountebank depending on the workload, with JSONPath predicates showing the most dramatic improvement.

## Getting Started

### Docker (Recommended)

```bash
docker run -p 2525:2525 ghcr.io/etacassiopeia/rift-proxy:latest
```

### Homebrew (macOS)

```bash
brew tap etacassiopeia/rift
brew install rift
```

### Cargo (Rust)

```bash
cargo install rift-http-proxy
```

### npm (Node.js projects)

```bash
npm install @rift-vs/rift
```

## Your First Mock in 60 Seconds

```bash
# 1. Start Rift
docker run -d -p 2525:2525 ghcr.io/etacassiopeia/rift-proxy:latest

# 2. Create a mock API
curl -X POST http://localhost:2525/imposters -H "Content-Type: application/json" -d '{
  "port": 4545,
  "protocol": "http",
  "stubs": [
    {
      "predicates": [{ "equals": { "path": "/api/users/1" } }],
      "responses": [{ "is": {
        "statusCode": 200,
        "headers": { "Content-Type": "application/json" },
        "body": "{\"id\": 1, \"name\": \"Alice\", \"email\": \"alice@example.com\"}"
      }}]
    },
    {
      "predicates": [{ "equals": { "path": "/api/users/999" } }],
      "responses": [{ "is": { "statusCode": 404, "body": "{\"error\": \"User not found\"}" }}]
    }
  ]
}'

# 3. Test it
curl http://localhost:4545/api/users/1
# {"id": 1, "name": "Alice", "email": "alice@example.com"}

curl http://localhost:4545/api/users/999
# {"error": "User not found"}
```

## Use Cases

- **Unit/Integration Testing**: Mock external dependencies for fast, reliable tests
- **Contract Testing**: Verify your app handles API responses correctly
- **Chaos Engineering**: Test how your system behaves under failure conditions
- **Development**: Work offline or without access to staging environments
- **Demo Environments**: Show features without real backend dependencies
- **Load Testing**: Consistent mock responses for benchmarking your application

## What's Coming in This Series

This is the first post in a comprehensive series:

1. **Introducing Rift** (this post)
2. **Getting Started with Rift in 5 Minutes**
3. **Migrating from Mountebank**
4. **Mastering Request Matching with Predicates**
5. **Chaos Engineering Made Easy: Fault Injection**
6. **Building Stateful Mock Services**
7. **Dynamic Responses with Scripting**
8. **Recording and Replaying API Traffic**
9. **Production-Ready Mocking: Docker, K8s, CI/CD**
10. **Quality Assurance with rift-verify and rift-lint**

## Resources

- [GitHub Repository](https://github.com/EtaCassiopeia/rift)
- [Documentation](https://etacassiopeia.github.io/rift/)
- [Examples](https://github.com/EtaCassiopeia/rift/tree/master/examples)

Rift is open source under the Apache 2.0 license.

---

*Next up: Getting Started with Rift in 5 Minutes — a hands-on guide to creating your first mock services.*

---

**Tags:** #APITesting #MockServer #ServiceVirtualization #Testing #DevOps #Rust #ChaosEngineering
