---
layout: default
title: Rift - High-Performance Mock Server
---

# Rift Documentation

Rift is a high-performance, Mountebank-compatible mock server written in Rust. It delivers 20-250x performance improvement while maintaining full API compatibility.

## Article Series

1. [Introducing Rift](posts/01-introducing-rift) - The Blazing-Fast Mountebank Alternative
2. [Getting Started](posts/02-getting-started) - Your First Mock Server in 5 Minutes
3. [Migration Guide](posts/03-migration-guide) - Seamless Transition from Mountebank
4. [Advanced Predicates](posts/04-advanced-predicates) - Mastering Request Matching
5. [Fault Injection](posts/05-fault-injection) - Chaos Engineering Made Simple
6. [Flow State](posts/06-flow-state) - Stateful Mocking with Rift
7. [Scripting](posts/07-scripting) - Dynamic Responses with Rhai, Lua, and JavaScript
8. [Proxy Mode](posts/08-proxy-mode) - Record and Replay Real API Traffic
9. [Production Deployment](posts/09-production-deployment) - Running Rift at Scale
10. [CLI Tools](posts/10-cli-tools) - rift-lint, rift-tui, and rift-verify

## Quick Start

```bash
# Using Docker
docker run -p 2525:2525 ghcr.io/etacassiopeia/rift-proxy:latest

# Using Homebrew (macOS)
brew install etacassiopeia/tap/rift

# Using Cargo
cargo install rift-http-proxy
```

## Resources

- [GitHub Repository](https://github.com/EtaCassiopeia/rift)
- [API Documentation](https://etacassiopeia.github.io/rift/)
- [npm Package](https://www.npmjs.com/package/@rift-vs/rift)
