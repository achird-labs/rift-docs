---
title: 'Rift - High-Performance Mock Server'
description: 'A high-performance, Mountebank-compatible mock server written in Rust, with 20-250x the throughput of Mountebank.'
audience: [evaluator]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Rift Documentation

Rift is a high-performance, Mountebank-compatible mock server written in Rust. It delivers 20-250x performance improvement while maintaining full API compatibility.

## Article Series

1. [Introducing Rift](articles/01-introducing-rift.md) - High-Performance API Mocking for Modern Development
2. [Getting Started](articles/02-getting-started.md) - Your First Mock Server in 5 Minutes
3. [Migration Guide](articles/03-migration-guide.md) - Seamless Transition from Mountebank
4. [Advanced Predicates](articles/04-advanced-predicates.md) - Mastering Request Matching
5. [Fault Injection](articles/05-fault-injection.md) - Chaos Engineering Made Simple
6. [Flow State](articles/06-flow-state.md) - Stateful Mocking with Rift
7. [Scripting](articles/07-scripting.md) - Dynamic Responses with Rhai, Lua, and JavaScript
8. [Proxy Mode](articles/08-proxy-mode.md) - Record and Replay Real API Traffic
9. [Production Deployment](articles/09-production-deployment.md) - Running Rift at Scale
10. [CLI Tools](articles/10-cli-tools.md) - rift-lint, rift-tui, and rift-verify

## Quick Start

```bash
# Using Docker
docker run -p 2525:2525 zainalpour/rift-proxy:latest

# Using Homebrew (macOS)
brew install achird-labs/rift/rift

# Using Cargo
cargo install rift-http-proxy
```

## Resources

- [GitHub Repository](https://github.com/achird-labs/rift)
- [API Documentation](https://achird-labs.github.io/rift/)
- [npm Package](https://www.npmjs.com/package/@rift-vs/rift)
