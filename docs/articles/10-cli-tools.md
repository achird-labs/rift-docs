---
title: 'Quality Assurance with rift-verify and rift-lint'
description: 'Validate imposter files with rift-lint and exercise a running server with rift-verify, locally and in CI.'
audience: [developer]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
upstream:
  - repo: achird-labs/rift
    paths:
      - docs/features/linting.md
      - docs/configuration/cli.md
      - crates/rift-http-proxy/src/bin/README.md
      - README.md
verified_against:
  rift: v0.18.1
---

# Quality Assurance with rift-verify and rift-lint

*Validate your mocks before they break your tests*

---

This article is for developers who keep imposter files in a repository and want them checked before
a test run depends on them. By the end you will lint those files, verify a running server's stubs,
and run both in CI.

You've built complex mock configurations. But how do you know they work correctly? How do you catch issues before they cause test failures?

Rift ships two CLI tools for this, alongside the `rift` server:

- **rift-lint**: validates configuration files before they are loaded
- **rift-verify**: sends a request to every stub of a running server and checks the response

Both are included in the Homebrew formula (`brew install achird-labs/rift/rift`) and the release
archives. `rift-lint` also has its own Docker image, `zainalpour/rift-lint`; `rift-verify` has none.

## rift-lint: Configuration Validation

### Basic Usage

```bash
# Lint a single file
rift-lint imposter.json

# Lint a directory
rift-lint ./imposters/

# Strict mode (treat warnings as errors)
rift-lint ./imposters/ --strict
```

`rift-lint` reads the same formats `--configfile` does — JSON (`.json`) and YAML (`.yaml`, `.yml`) —
and scans a directory one level deep, not recursively. It exits non-zero when it finds an error, or
a warning under `--strict`.

### What It Checks

Errors are problems Rift refuses or cannot serve correctly — for example a port declared twice
across the directory (`E002`), a stub with no `responses` (`E006`), an unknown predicate operator
(`E009`), or a header value that is a number or boolean instead of a string (`E019`, `E020`).
Warnings flag configurations that load but probably don't do what you meant — for example a stub
that uses state with no `_rift.flowState` configured (`W014`). The
[linting reference](https://achird-labs.github.io/rift/features/linting/) lists every code.

### Example Output

Two files that share a port, with a typo'd predicate and a numeric header:

```
Rift Imposter Linter
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scanning: .
Found:    2 imposter file(s)


FAIL order-service.json (2 error(s))
  | [port] error: Port 4545 is used by 2 imposters: order-service.json, user-service.json (E002)
  |   -> Assign unique ports to each imposter. Consider using ports 4546+
  | [stubs[0]] error: Stub missing 'responses' field (E006)

FAIL user-service.json (3 error(s))
  | [stubs[0].predicates[0]] error: Unknown predicate operator: eqauls (E009)
  |   -> Use one of: equals, deepEquals, contains, startsWith, endsWith, matches, exists, not, or, and, inject
  | [stubs[0].predicates[0]] error: Predicate has no operator (E008)
  |   -> Add one of: equals, deepEquals, contains, startsWith, endsWith, matches, exists, not, or, and, inject
  | [stubs[0].responses[0].is.headers.X-Count] error: Header 'X-Count' value is a number, must be a string (E019)
  |   -> Change to: "X-Count": "123"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Files checked: 2
  Errors:    5
  Warnings:  0

Linting failed with errors
```

### Auto-Fix Mode

Some issues can be fixed automatically:

```bash
rift-lint ./imposters/ --fix
```

`--fix` rewrites header values of the wrong type as strings — `123` becomes `"123"`, `true` becomes
`"true"` — in JSON files. Everything else it reports but leaves for you to fix.

### JSON Output for CI

```bash
rift-lint ./imposters/ --output json
```

The banner goes to stderr, so stdout is a single JSON document:

```json
{
  "issues": [
    {
      "severity": "error",
      "code": "E019",
      "message": "Header 'X-Count' value is a number, must be a string",
      "file": "./user-service.json",
      "location": "stubs[0].responses[0].is.headers.X-Count",
      "suggestion": "Change to: \"X-Count\": \"123\""
    }
  ],
  "files_checked": 2,
  "errors": 5,
  "warnings": 0
}
```

### CI/CD Integration

```yaml
# .github/workflows/lint.yml
name: Lint Mock Configs

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Lint configurations
        run: |
          docker run --rm -v ${{ github.workspace }}:/imposters \
            zainalpour/rift-lint:latest fixtures/ --strict --output json > lint-results.json

      - name: Upload results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: lint-results
          path: lint-results.json
```

### Checking Scripts

`rift-lint` checks a config's structure. To check the scripts inside it, use
`rift script check` — see [Scripting](07-scripting.md#testing-scripts-without-a-server).

## rift-verify: Stub Verification

### What It Does

rift-verify:

1. Fetches every imposter from a running Rift server's admin API
2. Builds a request from each stub's predicates
3. Sends it and compares the response with the stub's first response
4. Reports mismatches and exits non-zero if any test failed

### Basic Usage

```bash
# Verify every imposter on http://localhost:2525
rift-verify

# A different admin URL
rift-verify --admin-url http://localhost:3525

# One imposter
rift-verify --port 4545

# Print a curl command for each test, and every result rather than only failures
rift-verify --show-curl --verbose
```

### Example Output

This server has two imposters. In the Order Service, `GET /orders` answers `200`, and a second stub
catches every other `/orders` path with `404`:

```json
{
  "port": 4546,
  "protocol": "http",
  "name": "Order Service",
  "stubs": [
    {
      "predicates": [{ "equals": { "method": "GET", "path": "/orders" } }],
      "responses": [{ "is": { "statusCode": 200, "body": "[]" } }]
    },
    {
      "predicates": [{ "startsWith": { "path": "/orders" } }],
      "responses": [{ "is": { "statusCode": 404 } }]
    }
  ]
}
```

```
Rift Stub Verifier
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Admin URL: http://localhost:2525

Imposter: User Service (port 4545)

Imposter: Order Service (port 4546)
   FAIL Stub #1 - GET /orders

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verification Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Imposters:  2
  Stubs:      6
  Tests:      6

  Passed:  5
  Failed:  1
  Skipped: 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Failure Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Imposter :4546 (Order Service) - Stub #1
   Request:  GET /orders
   Expected: status=404, body=None
   Actual:   status=200, body=Some("[]")

   Why it failed:
   - Status mismatch: expected 404, got 200
     Hint: Expected status 404 but got 200. Verify the stub response configuration.

1 test(s) failed. See details above.
```

The failure is real, and it is the kind of bug rift-verify exists to find: the request generated
for stub #1 (`GET /orders`) is caught by stub #0 first, so stub #1 never answers that path. Stubs
match in order.

### Dynamic Stubs

A stub whose response is computed — `inject`, `proxy`, `_rift.script`, or a stub that cycles
through several responses — has no single expected answer. **By default rift-verify tests these
anyway** and expects a `200`, so a script that deliberately answers `418` is reported as a failure.
Skip them:

```bash
rift-verify --skip-dynamic
```

Or check only status codes, ignoring bodies and headers:

```bash
rift-verify --status-only
```

### Dry Run Mode

List what would be tested without sending any requests:

```bash
rift-verify --dry-run
```

```
Imposter: User Service (port 4545)
   DRY-RUN Stub #0 - GET /health
   DRY-RUN Stub #1 - GET /users
   DRY-RUN Stub #2 - POST /users
   DRY-RUN Stub #3 - GET /users/1

Imposter: Order Service (port 4546)
   DRY-RUN Stub #0 - GET /orders
   DRY-RUN Stub #1 - GET /orders
```

### JSON Output and Timeouts

```bash
# Machine-readable summary on stdout; progress goes to stderr
rift-verify --output json

# Per-request timeout in seconds (default 10)
rift-verify --timeout 30
```

```json
{
  "failed": 1,
  "imposters": 2,
  "passed": 5,
  "skipped": 0,
  "stubs": 6,
  "tests": 6
}
```

`rift-verify --help` lists the rest, including `--gateway` for servers reached through the
single-port gateway and `--insecure` for HTTPS imposters with self-signed certificates.

### CI Integration

```yaml
# GitHub Actions
- name: Verify mock stubs
  run: |
    # Start Rift
    docker run -d --name rift -p 2525:2525 -p 4545:4545 \
      -v ${{ github.workspace }}/fixtures:/fixtures \
      zainalpour/rift-proxy:latest \
      --configfile /fixtures/mocks.json

    # Wait until the admin API answers
    until curl -sf http://localhost:2525/ > /dev/null; do sleep 0.5; done

    # Verify (rift-verify must be installed on the runner)
    rift-verify --admin-url http://localhost:2525

    # Cleanup
    docker rm -f rift
```

## rift-tui: Interactive Management

Rift also includes an interactive terminal UI for managing a running server's imposters and stubs:

```bash
rift-tui                                     # http://localhost:2525
rift-tui --admin-url http://localhost:3525   # or RIFT_ADMIN_URL
```

See [TUI](https://achird-labs.github.io/rift/features/tui/) in the Rift docs for its screens and
key bindings.

## Combining Tools in Workflows

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Lint all imposter files
if ! rift-lint ./fixtures/ --strict; then
    echo "Imposter configuration has errors"
    exit 1
fi

echo "Imposter configurations are valid"
```

### Full Validation Pipeline

```bash
#!/bin/bash
# validate-mocks.sh

set -e

echo "Step 1: Linting configurations..."
rift-lint ./fixtures/ --strict

echo "Step 2: Starting Rift..."
rift --configfile ./fixtures/all.json &
RIFT_PID=$!
trap 'kill $RIFT_PID' EXIT
until rift healthcheck 2>/dev/null; do sleep 0.5; done

echo "Step 3: Verifying stubs..."
rift-verify --admin-url http://localhost:2525

echo "Step 4: Running integration tests..."
npm test

echo "All validations passed!"
```

`rift healthcheck` exits `0` once the admin API on `--port` (default `2525`) answers, which makes it
a better wait than a fixed `sleep`.

## Best Practices

### 1. Lint Early, Lint Often

```yaml
# Run on every commit
on: [push]
jobs:
  lint:
    steps:
      - run: rift-lint ./fixtures/ --strict
```

### 2. Verify After Changes

```bash
# After modifying configs
rift-lint ./fixtures/
rift-verify
```

### 3. Use Strict Mode in CI

```bash
# Fail on warnings in CI
rift-lint ./fixtures/ --strict --output json > results.json
```

### 4. Keep Verification Fast

```bash
# Skip dynamic stubs for quick feedback
rift-verify --skip-dynamic --timeout 5
```

### 5. Document Expected Failures

```bash
# When stubs intentionally cycle
rift-verify --status-only
```

## Troubleshooting

### Connection refused

```bash
# Ensure Rift is running
rift healthcheck
```

### Timeouts

```bash
# Increase timeout
rift-verify --timeout 60
```

### A dynamic stub reported as failed

```bash
# Skip inject, proxy, script and cycling stubs
rift-verify --skip-dynamic
```

## Conclusion: The Complete Series

We've covered everything you need to be productive with Rift:

1. **Introduction** — Why Rift, performance benefits
2. **Getting Started** — First imposters, basic usage
3. **Migration Guide** — Zero-friction Mountebank switch
4. **Advanced Predicates** — JSONPath, XPath, complex matching
5. **Fault Injection** — Chaos engineering made easy
6. **Flow State** — Stateful mock services
7. **Scripting** — Rhai and JavaScript engines
8. **Proxy Mode** — Recording and replaying
9. **Production Deployment** — Docker, K8s, CI/CD
10. **CLI Tools** — rift-verify and rift-lint (this post)

---

**Get Started Today:**

```bash
# Try Rift
docker run -p 2525:2525 zainalpour/rift-proxy:latest

# Star the repo
# https://github.com/achird-labs/rift
```

---

*Thank you for following this series! Questions? Feedback? Open an issue on GitHub.*

---

**Tags:** #CLI #Testing #QualityAssurance #MockServer #Rift #DevTools
