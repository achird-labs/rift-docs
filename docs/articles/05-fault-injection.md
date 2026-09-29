---
title: 'Chaos Engineering Made Easy: Fault Injection with Rift'
description: 'Test your application''s resilience without deploying to production.'
audience: [developer]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Chaos Engineering Made Easy: Fault Injection with Rift

*Test your application's resilience without deploying to production*

---

Your application works perfectly in ideal conditions. But what happens when:
- The payment service takes 5 seconds instead of 200ms?
- The authentication API returns 503 for 10% of requests?
- The database connection drops mid-request?

These scenarios are hard to reproduce in testing — but they happen in production. Chaos engineering helps you prepare.

Rift makes fault injection declarative and simple. No code changes. No complex setup. Just JSON configuration.

## The `_rift.fault` Extension

Rift extends Mountebank with native fault injection through the `_rift` namespace:

```json
{
  "is": { "statusCode": 200, "body": "OK" },
  "_rift": {
    "fault": {
      "latency": { "probability": 0.3, "minMs": 100, "maxMs": 500 }
    }
  }
}
```

This adds 100-500ms latency to 30% of responses. The other 70% respond normally.

## Latency Faults

### Fixed Delay

```json
{
  "_rift": {
    "fault": {
      "latency": {
        "probability": 1.0,
        "ms": 2000
      }
    }
  }
}
```

Every request takes exactly 2 seconds.

### Random Delay Range

```json
{
  "_rift": {
    "fault": {
      "latency": {
        "probability": 0.5,
        "minMs": 500,
        "maxMs": 3000
      }
    }
  }
}
```

50% of requests get 500-3000ms delay.

### Use Case: Timeout Testing

```json
{
  "port": 4545,
  "stubs": [{
    "predicates": [{ "equals": { "path": "/api/slow-service" } }],
    "responses": [{
      "is": { "statusCode": 200, "body": "Success" },
      "_rift": {
        "fault": {
          "latency": { "probability": 0.2, "ms": 10000 }
        }
      }
    }]
  }]
}
```

Test that your client properly times out and retries.

## Error Faults

### HTTP Error Responses

```json
{
  "_rift": {
    "fault": {
      "error": {
        "probability": 0.1,
        "status": 503,
        "body": "Service Unavailable",
        "headers": {
          "Retry-After": "30"
        }
      }
    }
  }
}
```

10% of requests return 503 with a Retry-After header.

### Multiple Error Types

```json
{
  "stubs": [
    {
      "predicates": [{ "equals": { "path": "/api/flaky" } }],
      "responses": [
        {
          "is": { "statusCode": 200, "body": "Success" },
          "_rift": {
            "fault": {
              "error": { "probability": 0.05, "status": 500 }
            }
          }
        },
        {
          "is": { "statusCode": 200, "body": "Success" },
          "_rift": {
            "fault": {
              "error": { "probability": 0.1, "status": 503 }
            }
          }
        },
        {
          "is": { "statusCode": 200, "body": "Success" },
          "_rift": {
            "fault": {
              "error": { "probability": 0.02, "status": 429 }
            }
          }
        }
      ]
    }
  ]
}
```

Response cycling with different fault probabilities simulates a realistically flaky service.

## TCP Faults

For testing connection-level failures:

### Connection Reset

```json
{
  "_rift": {
    "fault": {
      "tcp": {
        "probability": 0.05,
        "type": "reset"
      }
    }
  }
}
```

5% of connections receive RST (connection reset by peer).

### Connection Timeout

```json
{
  "_rift": {
    "fault": {
      "tcp": {
        "probability": 0.03,
        "type": "timeout"
      }
    }
  }
}
```

3% of connections hang indefinitely (until client timeout).

### Connection Close

```json
{
  "_rift": {
    "fault": {
      "tcp": {
        "probability": 0.02,
        "type": "close"
      }
    }
  }
}
```

2% of connections close without sending any response.

## Combining Faults

Stack multiple fault types:

```json
{
  "is": { "statusCode": 200, "body": "OK" },
  "_rift": {
    "fault": {
      "latency": {
        "probability": 0.3,
        "minMs": 100,
        "maxMs": 500
      },
      "error": {
        "probability": 0.1,
        "status": 503
      },
      "tcp": {
        "probability": 0.02,
        "type": "reset"
      }
    }
  }
}
```

**Order of evaluation:**
1. Latency applied first (the response is delayed), then evaluation continues
2. TCP fault checked (if triggered, the connection is reset and no HTTP response is sent)
3. Error fault applied only when no TCP fault fired

So latency + TCP is a delay-then-drop, and a TCP fault always wins over an error fault.

## Real-World Scenarios

### Scenario 1: Rate Limiting Simulation

```json
{
  "port": 4545,
  "stubs": [{
    "predicates": [{ "startsWith": { "path": "/api/" } }],
    "responses": [
      {
        "is": { "statusCode": 200, "body": "OK" },
        "_behaviors": { "repeat": 10 }
      },
      {
        "is": {
          "statusCode": 429,
          "headers": { "Retry-After": "60" },
          "body": { "error": "Rate limit exceeded" }
        }
      }
    ]
  }]
}
```

Allow 10 requests, then return 429. Cycles back to 200 after.

### Scenario 2: Cascading Failure

Simulate a degraded backend:

```json
{
  "port": 4545,
  "name": "Degraded Service",
  "stubs": [{
    "predicates": [{ "equals": { "path": "/health" } }],
    "responses": [{
      "is": { "statusCode": 200, "body": "healthy" }
    }]
  }, {
    "predicates": [{ "startsWith": { "path": "/api/" } }],
    "responses": [{
      "is": { "statusCode": 200 },
      "_rift": {
        "fault": {
          "latency": { "probability": 0.8, "minMs": 2000, "maxMs": 5000 },
          "error": { "probability": 0.3, "status": 503 }
        }
      }
    }]
  }]
}
```

Health check passes, but 80% of API calls are slow and 30% fail.

### Scenario 3: Network Partition

```json
{
  "port": 4545,
  "stubs": [{
    "responses": [{
      "is": { "statusCode": 200 },
      "_rift": {
        "fault": {
          "tcp": { "probability": 1.0, "type": "timeout" }
        }
      }
    }]
  }]
}
```

All connections hang — simulating complete network partition.

### Scenario 4: Retry Testing

```json
{
  "stubs": [{
    "predicates": [{ "equals": { "path": "/api/action" } }],
    "responses": [
      {
        "is": { "statusCode": 503, "body": "Unavailable" },
        "_behaviors": { "repeat": 2 }
      },
      {
        "is": { "statusCode": 200, "body": "Success!" }
      }
    ]
  }]
}
```

Fails twice, then succeeds. Perfect for testing retry logic.

### Scenario 5: Intermittent Failures

```json
{
  "stubs": [{
    "predicates": [{ "equals": { "path": "/api/unreliable" } }],
    "responses": [{
      "is": { "statusCode": 200, "body": "OK" },
      "_rift": {
        "fault": {
          "error": {
            "probability": 0.15,
            "status": 500,
            "body": { "error": "Internal server error", "transient": true }
          }
        }
      }
    }]
  }]
}
```

15% random failure rate — matches many real-world services.

## Monitoring Fault Injection

Rift exposes Prometheus metrics for fault injection:

```bash
curl http://localhost:9090/metrics | grep fault
```

```
# HELP rift_fault_injections_total Total fault injections
# TYPE rift_fault_injections_total counter
rift_fault_injections_total{type="latency"} 150
rift_fault_injections_total{type="error"} 42
rift_fault_injections_total{type="tcp_reset"} 3
```

Use these metrics to verify faults are being triggered as expected.

## Comparison: Rift vs Mountebank Fault Injection

| Feature | Mountebank | Rift |
|---------|------------|------|
| Latency simulation | `_behaviors.wait` | `_rift.fault.latency` |
| Probabilistic | Requires `inject` | Native support |
| TCP faults | Not supported | `_rift.fault.tcp` |
| Error injection | Manual with cycling | Native `_rift.fault.error` |
| Metrics | None | Prometheus |

Rift's fault injection is:
- **Declarative**: No JavaScript required
- **Probabilistic**: Built-in random distribution
- **Observable**: Prometheus metrics included

## Integration with Tests

### Jest Example

```javascript
describe('Resilience Tests', () => {
  beforeAll(async () => {
    await server.createImposter({
      port: 4545,
      stubs: [{
        responses: [{
          is: { statusCode: 200, body: 'OK' },
          _rift: {
            fault: {
              latency: { probability: 0.5, ms: 3000 }
            }
          }
        }]
      }]
    });
  });

  it('handles slow responses with timeout', async () => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);

    await expect(
      fetch('http://localhost:4545/api', { signal: controller.signal })
    ).rejects.toThrow('aborted');

    clearTimeout(timeout);
  });
});
```

### pytest Example

```python
def test_handles_service_errors(mock_server):
    mock_server.create_imposter({
        "port": 4545,
        "stubs": [{
            "responses": [{
                "is": {"statusCode": 200},
                "_rift": {
                    "fault": {
                        "error": {"probability": 1.0, "status": 503}
                    }
                }
            }]
        }]
    })

    with pytest.raises(ServiceUnavailable):
        client.call_service()
```

## Best Practices

1. **Start with low probabilities**: Begin at 5-10%, increase gradually
2. **Test one fault type at a time**: Isolate failure modes
3. **Monitor metrics**: Verify faults trigger at expected rates
4. **Combine with response cycling**: Create realistic failure patterns
5. **Document fault configurations**: Future you will thank you

## What's Next?

Fault injection tests single-request failures. But what about multi-step flows?

**Next Post**: Building Stateful Mock Services with Flow State

---

*What resilience patterns do you test for? Share your chaos engineering strategies in the comments!*

---

**Tags:** #ChaosEngineering #FaultInjection #Resilience #Testing #Rift #APITesting
