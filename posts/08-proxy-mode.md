---
layout: default
title: 'Recording and Replaying API Traffic with Proxy Mode'
---

# Recording and Replaying API Traffic with Proxy Mode

*Create mocks from real API behavior automatically*

---

Writing mock responses by hand is tedious and error-prone. What if you could:
- Point Rift at a real API
- Run your tests
- Have Rift record every response
- Replay those responses offline forever?

That's exactly what Proxy Mode does. Let's explore.

## How Proxy Mode Works

```
┌─────────┐    ┌──────────┐    ┌─────────────┐
│  Test   │───▶│   Rift   │───▶│  Real API   │
│  Suite  │◀───│ (Proxy)  │◀───│             │
└─────────┘    └──────────┘    └─────────────┘
                   │
                   ▼
              ┌──────────┐
              │ Recorded │
              │  Stubs   │
              └──────────┘
```

1. Request arrives at Rift
2. Rift forwards to real API
3. Response is recorded as a stub
4. Future matching requests use the recorded stub

## Proxy Modes

### proxyAlways

Always forward to real API, record every response:

```json
{
  "port": 4545,
  "stubs": [{
    "responses": [{
      "proxy": {
        "to": "https://api.example.com",
        "mode": "proxyAlways"
      }
    }]
  }]
}
```

**Use case**: Building a comprehensive mock from varied traffic.

### proxyOnce

Forward first request, replay recorded response for subsequent matching requests:

```json
{
  "proxy": {
    "to": "https://api.example.com",
    "mode": "proxyOnce"
  }
}
```

**Use case**: Creating stable test fixtures.

### proxyTransparent

Pure reverse proxy, no recording:

```json
{
  "proxy": {
    "to": "https://api.example.com",
    "mode": "proxyTransparent"
  }
}
```

**Use case**: Debugging, traffic inspection.

## The Recording Workflow

### Step 1: Create a Recording Proxy

```bash
curl -X POST http://localhost:2525/imposters \
  -H "Content-Type: application/json" \
  -d '{
    "port": 4545,
    "protocol": "http",
    "name": "API Recorder",
    "stubs": [{
      "responses": [{
        "proxy": {
          "to": "https://api.example.com",
          "mode": "proxyOnce",
          "predicateGenerators": [{
            "matches": {
              "method": true,
              "path": true,
              "query": true
            }
          }]
        }
      }]
    }]
  }'
```

### Step 2: Run Your Tests

Point your tests at the proxy:

```bash
# Instead of https://api.example.com
export API_URL=http://localhost:4545

npm test
```

Every API call is recorded.

### Step 3: Export Recorded Stubs

```bash
curl "http://localhost:2525/imposters/4545?replayable=true" > recorded.json
```

The `?replayable=true` parameter formats output for reloading.

### Step 4: Use Recorded Mocks

```bash
# Load recorded mocks (no proxy, pure playback)
curl -X DELETE http://localhost:2525/imposters/4545
curl -X POST http://localhost:2525/imposters \
  -H "Content-Type: application/json" \
  -d @recorded.json
```

Now your tests run offline with recorded responses.

## Predicate Generators

Control how Rift matches recorded responses to new requests:

### Match Everything

```json
{
  "predicateGenerators": [{
    "matches": {
      "method": true,
      "path": true,
      "query": true,
      "headers": true,
      "body": true
    }
  }]
}
```

Very specific — each unique request gets its own stub.

### Match Method and Path Only

```json
{
  "predicateGenerators": [{
    "matches": {
      "method": true,
      "path": true
    }
  }]
}
```

More flexible — ignores query strings and headers.

### Match with JSON Body

```json
{
  "predicateGenerators": [{
    "matches": {
      "method": true,
      "path": true
    }
  }, {
    "matches": {
      "body": true
    },
    "jsonpath": { "selector": "$.action" }
  }]
}
```

Match based on specific JSON fields.

## Path Rewriting

Modify paths before forwarding:

```json
{
  "proxy": {
    "to": "https://api.example.com",
    "pathRewrite": {
      "from": "/mock-api",
      "to": "/api"
    }
  }
}
```

Request to `/mock-api/users` forwards to `/api/users`.

### Use Case: API Versioning

```json
{
  "stubs": [{
    "predicates": [{ "startsWith": { "path": "/api/v2" } }],
    "responses": [{
      "proxy": {
        "to": "https://legacy.example.com",
        "pathRewrite": {
          "from": "/api/v2",
          "to": "/api/v1"
        }
      }
    }]
  }]
}
```

Route v2 requests to v1 backend during migration.

## Header Injection

Add headers to proxied requests:

```json
{
  "proxy": {
    "to": "https://api.example.com",
    "injectHeaders": {
      "X-Forwarded-By": "Rift",
      "Authorization": "Bearer internal-token",
      "X-Request-ID": "${uuid}"
    }
  }
}
```

Useful for:
- Adding authentication
- Tracking proxied requests
- Overriding client headers

## Response Transformation

### addDecorateBehavior

Transform responses before recording:

```json
{
  "proxy": {
    "to": "https://api.example.com",
    "addDecorateBehavior": "function(request, response) { \
      // Sanitize sensitive data \
      if (response.body.apiKey) { \
        response.body.apiKey = 'REDACTED'; \
      } \
      return response; \
    }"
  }
}
```

### addWaitBehavior

Add latency to proxied responses:

```json
{
  "proxy": {
    "to": "https://api.example.com",
    "addWaitBehavior": 100
  }
}
```

Simulates network latency in recorded stubs.

## Combining Proxy with Static Stubs

Mix recorded and static responses:

```json
{
  "port": 4545,
  "stubs": [
    {
      "predicates": [{ "equals": { "path": "/health" } }],
      "responses": [{
        "is": { "statusCode": 200, "body": "OK" }
      }]
    },
    {
      "predicates": [{ "equals": { "path": "/api/config" } }],
      "responses": [{
        "is": {
          "statusCode": 200,
          "body": { "feature_flags": { "new_ui": true } }
        }
      }]
    },
    {
      "responses": [{
        "proxy": {
          "to": "https://api.example.com",
          "mode": "proxyOnce"
        }
      }]
    }
  ]
}
```

Static stubs for controlled endpoints, proxy for everything else.

## HTTPS Proxying

### Basic HTTPS

```json
{
  "proxy": {
    "to": "https://secure-api.example.com"
  }
}
```

Rift handles TLS automatically.

### Skip Certificate Verification

For self-signed certs:

```json
{
  "proxy": {
    "to": "https://internal.local",
    "cert": null
  }
}
```

### Mutual TLS

```json
{
  "proxy": {
    "to": "https://api.example.com",
    "key": "-----BEGIN RSA PRIVATE KEY-----\n...",
    "cert": "-----BEGIN CERTIFICATE-----\n..."
  }
}
```

## Practical Workflows

### Contract Testing

1. Record production API responses
2. Run consumer tests against recordings
3. Catch breaking changes when recordings don't match

```bash
# Record from staging
PROXY_TARGET=https://staging.api.com ./record-fixtures.sh

# Test against recordings
npm test

# Compare with production
PROXY_TARGET=https://prod.api.com ./record-fixtures.sh
diff staging-fixtures.json prod-fixtures.json
```

### Offline Development

```bash
# Record once
docker run -v $(pwd):/data ghcr.io/etacassiopeia/rift-proxy \
  --configfile /data/proxy-config.json

# (run tests to record)

# Export
curl http://localhost:2525/imposters/4545?replayable=true > fixtures.json

# Develop offline forever
docker run -v $(pwd):/data ghcr.io/etacassiopeia/rift-proxy \
  --configfile /data/fixtures.json
```

### CI/CD with Recorded Fixtures

```yaml
# .github/workflows/test.yml
jobs:
  test:
    steps:
      - uses: actions/checkout@v4

      - name: Start mock server
        run: |
          docker run -d -p 2525:2525 -p 4545:4545 \
            -v ${{ github.workspace }}/fixtures:/fixtures \
            ghcr.io/etacassiopeia/rift-proxy \
            --configfile /fixtures/api-mocks.json

      - name: Run tests
        run: npm test
        env:
          API_URL: http://localhost:4545
```

## Save Command

Export imposters using the CLI:

```bash
# Save all imposters
rift-http-proxy save --savefile mocks.json

# Save without proxy stubs (pure responses)
rift-http-proxy save --savefile mocks.json --remove-proxies
```

The `--remove-proxies` flag removes proxy configurations, leaving only recorded responses.

## Best Practices

1. **Use consistent predicate generators**: Match enough to be specific, not so much that tests break on irrelevant changes

2. **Sanitize sensitive data**: Use `addDecorateBehavior` to redact tokens, keys, PII

3. **Version your fixtures**: Commit recorded responses to source control

4. **Record in isolation**: One service at a time for clearer fixtures

5. **Update regularly**: Re-record when APIs change

6. **Use proxyOnce for stability**: Avoid test flakiness from API changes

## What's Next?

You've got great mocks. Now let's deploy them:

**Next Post**: Production-Ready Mocking — Docker, Kubernetes, and CI/CD

---

*How do you manage API fixtures in your projects? Share your workflows!*

---

**Tags:** #ProxyMode #APIRecording #ContractTesting #MockServer #Rift #Testing
