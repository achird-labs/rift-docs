---
layout: default
title: 'Introducing Rift: The Blazing-Fast Mountebank Alternative That Will Transform Your API Testing'
---

# Introducing Rift: The Blazing-Fast Mountebank Alternative That Will Transform Your API Testing

*How a Rust rewrite delivers 20-250x performance improvement while maintaining full compatibility*

---

If you're using Mountebank for API mocking and service virtualization, you've probably experienced its pain points: slow startup times, memory-hungry processes, and test suites that take forever to run. What if I told you there's a drop-in replacement that's up to **250 times faster**?

Meet **Rift** — a high-performance, Mountebank-compatible mock server written in Rust that will fundamentally change how you think about API testing.

## The Problem with Traditional Mock Servers

API mocking is essential for modern software development. Whether you're testing microservices in isolation, simulating third-party APIs, or building contract tests, mock servers are indispensable. Mountebank has been the go-to solution for years, and for good reason — it's flexible, well-documented, and feature-rich.

But there's a catch.

As your test suite grows, Mountebank becomes a bottleneck:

- **Startup time**: Spinning up mock servers for each test adds up
- **Memory usage**: Each Node.js process consumes significant RAM
- **Throughput**: Complex predicates (JSONPath, XPath) can drop to ~100 requests per second
- **CI/CD costs**: Slow tests mean longer pipelines and higher cloud bills

I've worked on projects where the mock server setup took longer than the actual tests. That's backwards.

## Enter Rift: Same API, Incredible Performance

Rift is a complete reimplementation of Mountebank in Rust. But here's what makes it special — **you don't need to change anything**:

```bash
# Your existing Mountebank command
docker run -p 2525:2525 mountebank/mountebank

# Simply becomes
docker run -p 2525:2525 ghcr.io/etacassiopeia/rift-proxy:latest
```

Your `imposters.json` files? They work unchanged. Your test code that calls the REST API? No modifications needed. Your CI/CD scripts? Just swap the image name.

### The Numbers Don't Lie

Here's what we measured in real-world benchmarks:

| Scenario | Mountebank | Rift | Improvement |
|:---------|:-----------|:-----|:------------|
| Simple stub matching | 1,900 RPS | 39,000 RPS | **20x faster** |
| JSONPath predicates | 107 RPS | 26,500 RPS | **247x faster** |
| XPath predicates | 169 RPS | 28,700 RPS | **170x faster** |
| Complex AND/OR predicates | 900 RPS | 29,300 RPS | **32x faster** |
| High concurrency (100 connections) | 1,800 RPS | 29,700 RPS | **16x faster** |

The JSONPath improvement is particularly striking. If your tests rely heavily on JSON body matching, you'll see dramatic speedups.

## Why Rust Makes the Difference

Rift's performance comes from Rust's zero-cost abstractions and memory safety without garbage collection:

1. **No GC pauses**: Rust's ownership model eliminates garbage collection entirely
2. **Async I/O**: Built on Tokio, handling thousands of concurrent connections efficiently
3. **Zero-copy parsing**: JSON and XML processing without unnecessary allocations
4. **Native binaries**: No runtime interpretation overhead

But performance isn't the only benefit. Rust's type system catches bugs at compile time that would be runtime errors in JavaScript. The result is a more reliable mock server.

## Full Mountebank Compatibility

Rift implements the complete Mountebank feature set:

**Predicates:**
- `equals`, `deepEquals` — Exact matching
- `contains`, `startsWith`, `endsWith` — Partial matching
- `matches` — Regular expressions
- `exists` — Field presence checking
- `jsonpath`, `xpath` — Structured data queries
- `and`, `or`, `not` — Logical operators

**Responses:**
- Static responses (`is`)
- Proxy responses with recording
- JavaScript injection (`inject`)

**Behaviors:**
- `wait` — Latency simulation
- `decorate` — Response transformation
- `copy` — Request data extraction
- `lookup` — External data sources
- `repeat` — Response cycling

## Beyond Mountebank: Rift Extensions

While maintaining compatibility, Rift adds powerful features through the `_rift` namespace:

### Native Fault Injection

```json
{
  "is": { "statusCode": 200, "body": "OK" },
  "_rift": {
    "fault": {
      "latency": { "probability": 0.3, "minMs": 100, "maxMs": 500 },
      "error": { "probability": 0.1, "status": 503 }
    }
  }
}
```

No JavaScript required — just declarative chaos engineering.

### Multi-Engine Scripting

Choose the right language for your team:

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "let count = flow.get('count') + 1; flow.set('count', count); #{ statusCode: 200, body: `Request #${count}` }"
    }
  }
}
```

Rift supports Rhai (built-in, sandboxed), Lua, and JavaScript.

### Stateful Testing with Flow State

Build complex multi-step test scenarios:

```json
{
  "_rift": {
    "flowState": {
      "backend": "redis",
      "ttlSeconds": 300
    }
  }
}
```

State persists across requests, enabling scenarios like:
- Authentication flows
- Shopping cart simulations
- Rate limiting tests
- Retry mechanism validation

## Getting Started in 60 Seconds

```bash
# Pull the Docker image
docker pull ghcr.io/etacassiopeia/rift-proxy:latest

# Start Rift
docker run -p 2525:2525 ghcr.io/etacassiopeia/rift-proxy:latest

# Create your first imposter
curl -X POST http://localhost:2525/imposters \
  -H "Content-Type: application/json" \
  -d '{
    "port": 4545,
    "protocol": "http",
    "stubs": [{
      "predicates": [{ "equals": { "path": "/hello" } }],
      "responses": [{ "is": { "statusCode": 200, "body": "Hello from Rift!" } }]
    }]
  }'

# Test it
curl http://localhost:4545/hello
# Output: Hello from Rift!
```

Already using Mountebank? Just mount your existing config:

```bash
docker run -p 2525:2525 \
  -v $(pwd)/imposters.json:/imposters.json \
  ghcr.io/etacassiopeia/rift-proxy:latest \
  --configfile /imposters.json
```

## What's Coming in This Series

This is the first post in a comprehensive series on Rift:

1. **Introducing Rift** (this post)
2. **Getting Started with Rift in 5 Minutes**
3. **Migrating from Mountebank: A Zero-Friction Guide**
4. **Mastering Request Matching with Predicates**
5. **Chaos Engineering Made Easy: Fault Injection**
6. **Building Stateful Mock Services**
7. **Dynamic Responses with Multi-Engine Scripting**
8. **Recording and Replaying API Traffic**
9. **Production-Ready Mocking: Docker, K8s, CI/CD**
10. **Quality Assurance with rift-verify and rift-lint**

## Try It Today

Rift is open source under the Apache 2.0 license. The easiest way to try it:

```bash
docker run -p 2525:2525 ghcr.io/etacassiopeia/rift-proxy:latest
```

Or install via Homebrew:

```bash
brew tap etacassiopeia/rift
brew install rift
```

**Resources:**
- [GitHub Repository](https://github.com/EtaCassiopeia/rift)
- [Documentation](https://etacassiopeia.github.io/rift/)
- [Examples](https://github.com/EtaCassiopeia/rift/tree/master/examples)

---

*Have you tried Rift? I'd love to hear about your experience. Drop a comment below or star the repo on GitHub!*

*Next up: Getting Started with Rift in 5 Minutes — a hands-on guide to creating your first mock services.*

---

**Tags:** #APITesting #Mountebank #Rust #MockServer #ServiceVirtualization #Testing #DevOps #Performance
