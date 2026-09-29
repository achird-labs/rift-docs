---
title: 'Migrating from Mountebank to Rift: A Zero-Friction Guide'
description: 'Switch to 20-250x better performance without changing a single line of configuration.'
audience: [developer, evaluator]
deployment_mode: [container]
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Migrating from Mountebank to Rift: A Zero-Friction Guide

*Switch to 20-250x better performance without changing a single line of configuration*

---

You're using Mountebank. Your team has invested time building mock configurations, your CI/CD pipelines are set up, and your tests depend on it. The thought of migration sounds daunting.

Here's the good news: **migrating to Rift takes about 5 minutes**.

Rift is designed as a drop-in replacement. Same API. Same configuration format. Same behavior. Just faster. Much faster.

## The 5-Minute Migration

### Step 1: Swap the Docker Image

**Before (Mountebank):**
```bash
docker run -p 2525:2525 mountebank/mountebank:2.9.1
```

**After (Rift):**
```bash
docker run -p 2525:2525 zainalpour/rift-proxy:latest
```

That's it. Your existing `imposters.json` files work without modification.

### Step 2: Update docker-compose.yml

**Before:**
```yaml
services:
  mountebank:
    image: mountebank/mountebank:2.9.1
    ports:
      - "2525:2525"
      - "4545:4545"
    volumes:
      - ./imposters.json:/imposters.json
    command: --configfile /imposters.json --allowInjection
```

**After:**
```yaml
services:
  rift:
    image: zainalpour/rift-proxy:latest
    ports:
      - "2525:2525"
      - "4545:4545"
    volumes:
      - ./imposters.json:/imposters.json
    command: --configfile /imposters.json --allow-injection
```

Note: `--allowInjection` becomes `--allow-injection` (both are supported for compatibility).

### Step 3: Update CI/CD

If you're pulling from Docker Hub, update the image reference:

```yaml
# GitHub Actions example
jobs:
  test:
    services:
      rift:
        image: zainalpour/rift-proxy:latest
        ports:
          - 2525:2525
```

## Compatibility Checklist

| Feature | Mountebank | Rift | Notes |
|---------|------------|------|-------|
| REST API | ✅ | ✅ | Identical |
| JSON config format | ✅ | ✅ | Identical |
| `equals` predicate | ✅ | ✅ | |
| `deepEquals` predicate | ✅ | ✅ | |
| `contains` predicate | ✅ | ✅ | |
| `startsWith` predicate | ✅ | ✅ | |
| `endsWith` predicate | ✅ | ✅ | |
| `matches` (regex) | ✅ | ✅ | |
| `exists` predicate | ✅ | ✅ | |
| `jsonpath` predicate | ✅ | ✅ | 247x faster |
| `xpath` predicate | ✅ | ✅ | 170x faster |
| `and`/`or`/`not` | ✅ | ✅ | |
| `is` response | ✅ | ✅ | |
| `proxy` response | ✅ | ✅ | |
| `inject` response | ✅ | ✅ | JavaScript |
| `wait` behavior | ✅ | ✅ | |
| `decorate` behavior | ✅ | ✅ | |
| `copy` behavior | ✅ | ✅ | |
| `lookup` behavior | ✅ | ✅ | |
| `repeat` behavior | ✅ | ✅ | |
| Response cycling | ✅ | ✅ | |
| Request recording | ✅ | ✅ | |
| HTTPS | ✅ | ✅ | |
| Mutual TLS | ✅ | ✅ | |

## Validating Your Migration

### Using rift-verify

Rift includes a verification tool that tests your imposters automatically:

```bash
# Start Rift with your config
docker run -d -p 2525:2525 -p 4545:4545 \
  -v $(pwd)/imposters.json:/imposters.json \
  zainalpour/rift-proxy:latest \
  --configfile /imposters.json

# Run verification (rift-verify ships with the Homebrew formula and the release archives)
rift-verify --admin-url http://localhost:2525
```

The verifier:
- Fetches all imposters
- Generates test requests from predicates
- Verifies responses match expectations
- Reports any mismatches

### Using rift-lint

Validate configuration before deployment:

```bash
# Check for issues
rift-lint ./imposters/

# Strict mode (CI/CD)
rift-lint ./imposters/ --strict

# Auto-fix common issues
rift-lint ./imposters/ --fix
```

## Migration Scenarios

### Scenario 1: Kubernetes Deployment

**Before:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mountebank
spec:
  template:
    spec:
      containers:
        - name: mountebank
          image: mountebank/mountebank:2.9.1
          ports:
            - containerPort: 2525
```

**After:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rift
spec:
  template:
    spec:
      containers:
        - name: rift
          image: zainalpour/rift-proxy:latest
          ports:
            - containerPort: 2525
          resources:
            # Rift uses significantly less memory
            limits:
              memory: "128Mi"  # vs 512Mi+ for Mountebank
              cpu: "500m"
```

### Scenario 2: Node.js Test Suite

If you're using the `mountebank` npm package:

**Before:**
```javascript
const mb = require('mountebank');

const server = await mb.create({ port: 2525 });
```

**After:**
```javascript
import rift from '@rift-vs/rift';

const server = await rift.create({ port: 2525 });
```

The API is intentionally similar. Most test code requires minimal changes.

### Scenario 3: Python Tests with requests

No changes needed — you're calling the REST API:

```python
import requests

# This works with both Mountebank and Rift
def create_imposter(port, stubs):
    requests.post('http://localhost:2525/imposters', json={
        'port': port,
        'protocol': 'http',
        'stubs': stubs
    })
```

## Common Migration Issues

### Issue 1: EJS Templates

Mountebank supports EJS templates in config files. Rift currently processes these statically at load time.

**Solution:** Pre-process EJS files or use environment variable substitution:

```bash
# Use envsubst
envsubst < imposters.template.json > imposters.json
rift --configfile imposters.json
```

### Issue 2: File Includes

Mountebank's `<%- include('...') %>` syntax works in Rift for reading files (certificates, etc.):

```json
{
  "protocol": "https",
  "key": "<%- include('/certs/key.pem') %>",
  "cert": "<%- include('/certs/cert.pem') %>"
}
```

### Issue 3: Custom Mountebank Protocols

Rift currently supports HTTP/HTTPS. TCP and SMTP protocols are planned.

**Workaround:** Run Mountebank alongside Rift for unsupported protocols:

```yaml
services:
  rift:
    image: zainalpour/rift-proxy:latest
    ports:
      - "2525:2525"
      - "4545-4555:4545-4555"  # HTTP mocks

  mountebank:
    image: mountebank/mountebank:2.9.1
    ports:
      - "2526:2525"
      - "4556-4560:4556-4560"  # TCP/SMTP mocks
```

## Performance Comparison

After migration, you'll notice immediate improvements:

### Startup Time

```bash
# Mountebank with 10 imposters
time docker run mountebank/mountebank --configfile imposters.json
# ~3-5 seconds

# Rift with 10 imposters
time docker run zainalpour/rift-proxy --configfile imposters.json
# ~0.5 seconds
```

### Memory Usage

```bash
# Mountebank
docker stats mountebank
# CONTAINER   CPU %   MEM USAGE
# mountebank  0.50%   180MiB

# Rift
docker stats rift
# CONTAINER   CPU %   MEM USAGE
# rift        0.10%   15MiB
```

### Request Throughput

Run a quick benchmark:

```bash
# Install hey
brew install hey

# Benchmark
hey -n 10000 -c 50 http://localhost:4545/api/users
```

You'll see significantly higher requests per second with Rift.

## Gradual Migration Strategy

For large teams, consider a gradual approach:

### Phase 1: New Projects
Use Rift for all new test suites and services.

### Phase 2: Non-Critical Tests
Migrate integration tests that run frequently (biggest performance gain).

### Phase 3: Full Migration
After validation, migrate remaining Mountebank usage.

### Parallel Running
During transition, run both in parallel:

```yaml
services:
  rift:
    image: zainalpour/rift-proxy:latest
    ports:
      - "2525:2525"
    environment:
      - RUST_LOG=info

  mountebank:
    image: mountebank/mountebank:2.9.1
    ports:
      - "2526:2525"  # Different port
```

Route traffic based on test suite or feature flag.

## Migration Checklist

- [ ] Update Docker image reference
- [ ] Update docker-compose.yml
- [ ] Update CI/CD configuration
- [ ] Run rift-lint on configuration files
- [ ] Run rift-verify to validate imposters
- [ ] Run existing test suite
- [ ] Monitor for any behavioral differences
- [ ] Update documentation

## Getting Help

Encountering issues? Here's where to get help:

1. **Documentation**: [achird-labs.github.io/rift](https://achird-labs.github.io/rift/)
2. **GitHub Issues**: Report bugs or compatibility issues
3. **Examples**: Check the examples directory for patterns

## What's Next?

You've migrated to Rift. Now let's explore advanced features:

- **Next Post**: Mastering Request Matching with Predicates
- **Coming Soon**: Chaos Engineering with Fault Injection

---

*Successfully migrated? Share your experience! How much faster are your tests running?*

---

**Tags:** #Migration #Mountebank #Rift #APITesting #DevOps #Performance
