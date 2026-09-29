---
title: 'Quality Assurance with rift-verify and rift-lint'
description: 'Validate your mocks before they break your tests.'
audience: [developer]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Quality Assurance with rift-verify and rift-lint

*Validate your mocks before they break your tests*

---

You've built complex mock configurations. But how do you know they work correctly? How do you catch issues before they cause test failures?

Rift includes two powerful CLI tools:
- **rift-lint**: Validate configurations before loading
- **rift-verify**: Test imposters by generating requests

Let's explore how to use them effectively.

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
and scans a directory one level deep, not recursively.

### What It Checks

**Errors (prevent loading):**
- Files that cannot be read or are not valid JSON or YAML
- Missing required fields (`port`, `protocol`, `stubs`)
- Port conflicts — the same port declared twice, inside one file or across files in the directory
  (`E002`)
- Invalid predicate structures
- Malformed behaviors

**Warnings (potential issues):**
- Privileged ports
- A body that is not JSON under a JSON `Content-Type`
- Unknown proxy modes and potentially dangerous `shellTransform` commands
- Keys the engine parses but does not act on (`W017`)
- A `behaviors` array element that sets several behaviors, so they run in a fixed order rather than
  the order written (`W018`)

### Example Output

```
Rift Imposter Linter
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scanning: ./imposters/
Found:    5 imposter file(s)

FAIL user-service.json (3 error(s))
  | [stubs[0].responses[0].is.headers.X-Count] ERROR: Header 'X-Count' value is a number, must be a string (E019)
  |   -> Change to: "X-Count": "123"
  | [stubs[1].predicates[0]] ERROR: Unknown predicate operator: eqauls (E009)
  |   -> Use one of: equals, deepEquals, contains, ...
  | [port] ERROR: Port 4545 is used by 2 imposters: user-service.json, order-service.json (E002)
  |   -> Assign unique ports to each imposter. Consider using ports 4546+

WARN order-service.json (1 warning(s))
  | [stubs[0]] WARNING: Stub has no responses defined (W002)
  |   -> Add at least one response

PASS payment-service.json
PASS auth-service.json
PASS config-service.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Files checked: 5
  Errors:    3
  Warnings:  1

Linting failed with errors
```

### Auto-Fix Mode

Some issues can be fixed automatically:

```bash
rift-lint ./imposters/ --fix
```

`--fix` corrects value shapes in `is.headers` (the `E018`, `E019` and `E020` findings):
- A number → the same number as a string
- A boolean → the same boolean as a string
- An array containing a non-string element → each element quoted in place (a string-only array is
  already legal and is left alone)

It rewrites JSON files only; a YAML file, a templated file, or a file that repeats a key is reported
but never rewritten.

### JSON Output for CI

```bash
rift-lint ./imposters/ --output json
```

```json
{
  "files_checked": 5,
  "errors": 3,
  "warnings": 1,
  "issues": [
    {
      "severity": "error",
      "code": "E019",
      "message": "Header 'X-Count' value is a number, must be a string",
      "file": "user-service.json",
      "location": "stubs[0].responses[0].is.headers.X-Count",
      "suggestion": "Change to: \"X-Count\": \"123\""
    }
  ]
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

## rift-verify: Stub Verification

### What It Does

rift-verify:
1. Fetches all imposters from a running Rift server
2. Analyzes predicates to generate matching requests
3. Makes requests and verifies responses
4. Reports any mismatches

### Basic Usage

```bash
# Verify all imposters
rift-verify

# Verify specific imposter
rift-verify --port 4545

# Show curl commands for each test
rift-verify --show-curl

# Verbose output
rift-verify --verbose
```

### Example Output

```
Rift Stub Verifier
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Admin URL: http://localhost:2525
Found: 3 imposters

Imposter :4545 (User Service)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ GET /health → 200 OK
  ✓ GET /users → 200 OK (12 items)
  ✓ POST /users → 201 Created
  ✗ DELETE /users/123 → Expected 204, got 404

  curl -X DELETE http://localhost:4545/users/123

Imposter :4546 (Order Service)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ GET /orders → 200 OK
  ✓ POST /orders → 201 Created
  ~ SKIP GET /orders/{id} → Dynamic predicate (matches)

Imposter :4547 (Payment Service)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ POST /payments → 200 OK
  ✓ GET /payments/status → 200 OK

Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total: 9 stubs
  Passed: 7
  Failed: 1
  Skipped: 1

Verification failed
```

### Show Curl Commands

```bash
rift-verify --show-curl
```

Output includes ready-to-use curl commands:

```
✗ DELETE /users/123 → Expected 204, got 404

  Reproduce with:
  curl -X DELETE http://localhost:4545/users/123 \
    -H "Content-Type: application/json"
```

### Skip Dynamic Stubs

Some stubs can't be verified automatically (inject, proxy, complex scripts):

```bash
# Skip stubs with dynamic responses
rift-verify --skip-dynamic
```

### Dry Run Mode

See what would be tested without making requests:

```bash
rift-verify --dry-run
```

```
Dry Run - Would test:
  :4545 GET /health
  :4545 GET /users
  :4545 POST /users
  :4545 DELETE /users/123
  :4546 GET /orders
  ...
```

### Status-Only Mode

Only verify status codes (useful for cycling responses):

```bash
rift-verify --status-only
```

### Custom Timeout

```bash
rift-verify --timeout 30
```

### CI Integration

```yaml
# GitHub Actions
- name: Verify mock stubs
  run: |
    # Start Rift
    docker run -d -p 2525:2525 -p 4545:4545 \
      -v ${{ github.workspace }}/fixtures:/fixtures \
      zainalpour/rift-proxy:latest \
      --configfile /fixtures/mocks.json

    # Wait for startup
    sleep 3

    # Verify
    rift-verify --admin-url http://localhost:2525

    # Cleanup
    docker stop $(docker ps -q --filter ancestor=zainalpour/rift-proxy)
```

## rift-tui: Interactive Management

Rift also includes an interactive terminal UI:

```bash
rift-tui
```

### Features

- **View imposters**: Navigate with j/k (vim-style)
- **Inspect stubs**: See predicates and responses
- **Generate curl**: Copy test commands
- **Real-time metrics**: Request counts, latencies
- **Edit configuration**: Modify stubs live

### Screenshots

```
┌─ Imposters ─────────────────────────────────────┐
│ ► :4545 User Service        [3 stubs] [47 req] │
│   :4546 Order Service       [2 stubs] [12 req] │
│   :4547 Payment Service     [4 stubs] [8 req]  │
└─────────────────────────────────────────────────┘
┌─ Stubs ─────────────────────────────────────────┐
│ GET /health                 → 200 OK           │
│ GET /users                  → 200 [array]      │
│ POST /users                 → 201 Created      │
└─────────────────────────────────────────────────┘
┌─ Response Preview ──────────────────────────────┐
│ {                                               │
│   "id": 1,                                      │
│   "name": "Alice",                              │
│   "email": "alice@example.com"                  │
│ }                                               │
└─────────────────────────────────────────────────┘
  [q]uit  [r]efresh  [c]url  [e]dit  [d]elete
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `j/k` | Navigate up/down |
| `Enter` | Select/expand |
| `c` | Copy curl command |
| `e` | Edit stub |
| `d` | Delete stub |
| `r` | Refresh |
| `q` | Quit |

## Combining Tools in Workflows

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Lint all imposter files
if ! rift-lint ./fixtures/ --strict; then
    echo "❌ Imposter configuration has errors"
    exit 1
fi

echo "✓ Imposter configurations are valid"
```

### Full Validation Pipeline

```bash
#!/bin/bash
# validate-mocks.sh

set -e

echo "Step 1: Linting configurations..."
rift-lint ./fixtures/ --strict

echo "Step 2: Starting Rift..."
rift-http-proxy --configfile ./fixtures/all.json &
RIFT_PID=$!
sleep 2

echo "Step 3: Verifying stubs..."
rift-verify --admin-url http://localhost:2525

echo "Step 4: Running integration tests..."
npm test

echo "Cleaning up..."
kill $RIFT_PID

echo "✓ All validations passed!"
```

### Docker-Based Validation

```bash
# Lint
docker run --rm \
  -v $(pwd)/fixtures:/fixtures \
  zainalpour/rift-lint /fixtures --strict

# Verify
docker run -d --name rift -p 2525:2525 \
  -v $(pwd)/fixtures:/fixtures \
  zainalpour/rift-proxy:latest \
  --configfile /fixtures/all.json

sleep 2

docker run --rm --network host \
  ghcr.io/etacassiopeia/rift-verify

docker rm -f rift
```

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
# When stubs intentionally cycle/fail
rift-verify --status-only
```

## Troubleshooting

### "Connection refused"

```bash
# Ensure Rift is running
curl http://localhost:2525/
```

### "Timeout waiting for response"

```bash
# Increase timeout
rift-verify --timeout 60
```

### "Predicate too complex to generate request"

```bash
# Skip complex predicates
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
7. **Scripting** — Rhai, Lua, JavaScript engines
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

*Thank you for following this series! Questions? Feedback? Open an issue on GitHub or comment below.*

---

**Tags:** #CLI #Testing #QualityAssurance #MockServer #Rift #DevTools
