---
layout: default
title: 'Building Stateful Mock Services with Flow State'
---

# Building Stateful Mock Services with Flow State

*From simple stubs to complex multi-step test scenarios*

---

Most mock servers are stateless. Each request is independent. But real APIs have state:
- Login creates a session
- Adding items updates a cart
- Rate limits track request counts
- Transactions progress through stages

Rift's **Flow State** feature lets you build mocks that remember. Track state across requests, implement complex flows, and test scenarios that were previously impossible.

## Understanding Flow State

Flow State provides a key-value store accessible from your mock responses:

```json
{
  "port": 4545,
  "_rift": {
    "flowState": {
      "backend": "inmemory",
      "ttlSeconds": 300
    }
  },
  "stubs": [...]
}
```

Scripts can read and write to this store, enabling stateful behavior.

## Backend Options

### In-Memory (Default)

```json
{
  "_rift": {
    "flowState": {
      "backend": "inmemory",
      "ttlSeconds": 300
    }
  }
}
```

- **Pros**: Zero setup, fast
- **Cons**: Lost on restart, single instance only
- **Use for**: Local development, single-instance testing

### Redis (Distributed)

```json
{
  "_rift": {
    "flowState": {
      "backend": "redis",
      "ttlSeconds": 600,
      "redis": {
        "url": "redis://localhost:6379",
        "poolSize": 10,
        "keyPrefix": "rift:test:"
      }
    }
  }
}
```

- **Pros**: Persistent, shared across instances
- **Cons**: Requires Redis server
- **Use for**: CI/CD, distributed testing, production mocks

## Basic Counter Example

Track how many times an endpoint is called:

```json
{
  "port": 4545,
  "_rift": {
    "flowState": { "backend": "inmemory" }
  },
  "stubs": [{
    "predicates": [{ "equals": { "path": "/counter" } }],
    "responses": [{
      "_rift": {
        "script": {
          "engine": "rhai",
          "code": "let count = flow.get('count').unwrap_or(0) + 1; flow.set('count', count); #{ statusCode: 200, body: `Count: ${count}` }"
        }
      }
    }]
  }]
}
```

```bash
curl http://localhost:4545/counter  # Count: 1
curl http://localhost:4545/counter  # Count: 2
curl http://localhost:4545/counter  # Count: 3
```

## Real-World Scenario: Rate Limiting

Implement a rate limiter that allows 10 requests per minute:

```json
{
  "port": 4545,
  "_rift": {
    "flowState": { "backend": "inmemory", "ttlSeconds": 60 }
  },
  "stubs": [{
    "predicates": [{ "startsWith": { "path": "/api/" } }],
    "responses": [{
      "_rift": {
        "script": {
          "engine": "rhai",
          "code": "
            let count = flow.get('requests').unwrap_or(0) + 1;
            flow.set('requests', count);

            if count > 10 {
              #{
                statusCode: 429,
                headers: #{ 'Retry-After': '60' },
                body: #{ error: 'Rate limit exceeded', limit: 10, remaining: 0 }
              }
            } else {
              #{
                statusCode: 200,
                headers: #{ 'X-RateLimit-Remaining': `${10 - count}` },
                body: #{ data: 'OK', remaining: 10 - count }
              }
            }
          "
        }
      }
    }]
  }]
}
```

The TTL of 60 seconds resets the counter automatically.

## Real-World Scenario: Authentication Flow

Simulate login/logout with session tracking:

```json
{
  "port": 4545,
  "_rift": {
    "flowState": { "backend": "inmemory", "ttlSeconds": 3600 }
  },
  "stubs": [
    {
      "predicates": [
        { "equals": { "method": "POST", "path": "/login" } }
      ],
      "responses": [{
        "_rift": {
          "script": {
            "engine": "rhai",
            "code": "
              let session_id = `sess_${timestamp()}`;
              flow.set('session', session_id);
              flow.set('user', 'alice');
              #{
                statusCode: 200,
                headers: #{ 'Set-Cookie': `session=${session_id}` },
                body: #{ success: true, user: 'alice' }
              }
            "
          }
        }
      }]
    },
    {
      "predicates": [
        { "equals": { "path": "/profile" } }
      ],
      "responses": [{
        "_rift": {
          "script": {
            "engine": "rhai",
            "code": "
              let session = flow.get('session');
              if session.is_some() {
                let user = flow.get('user').unwrap_or('unknown');
                #{ statusCode: 200, body: #{ user: user, authenticated: true } }
              } else {
                #{ statusCode: 401, body: #{ error: 'Not authenticated' } }
              }
            "
          }
        }
      }]
    },
    {
      "predicates": [
        { "equals": { "method": "POST", "path": "/logout" } }
      ],
      "responses": [{
        "_rift": {
          "script": {
            "engine": "rhai",
            "code": "
              flow.delete('session');
              flow.delete('user');
              #{ statusCode: 200, body: #{ success: true } }
            "
          }
        }
      }]
    }
  ]
}
```

Test the flow:

```bash
# Before login
curl http://localhost:4545/profile
# {"error": "Not authenticated"}

# Login
curl -X POST http://localhost:4545/login
# {"success": true, "user": "alice"}

# After login
curl http://localhost:4545/profile
# {"user": "alice", "authenticated": true}

# Logout
curl -X POST http://localhost:4545/logout

# After logout
curl http://localhost:4545/profile
# {"error": "Not authenticated"}
```

## Real-World Scenario: Shopping Cart

```json
{
  "port": 4545,
  "_rift": {
    "flowState": { "backend": "inmemory" }
  },
  "stubs": [
    {
      "predicates": [{ "equals": { "method": "GET", "path": "/cart" } }],
      "responses": [{
        "_rift": {
          "script": {
            "engine": "rhai",
            "code": "
              let items = flow.get('cart_items').unwrap_or([]);
              let total = 0.0;
              for item in items { total += item.price * item.quantity; }
              #{
                statusCode: 200,
                body: #{ items: items, total: total, count: items.len() }
              }
            "
          }
        }
      }]
    },
    {
      "predicates": [{ "equals": { "method": "POST", "path": "/cart/add" } }],
      "responses": [{
        "_rift": {
          "script": {
            "engine": "rhai",
            "code": "
              let items = flow.get('cart_items').unwrap_or([]);
              let body = parse_json(request.body);
              items.push(#{
                sku: body.sku,
                name: body.name,
                price: body.price,
                quantity: body.quantity
              });
              flow.set('cart_items', items);
              #{ statusCode: 201, body: #{ added: true, cartSize: items.len() } }
            "
          }
        }
      }]
    },
    {
      "predicates": [{ "equals": { "method": "DELETE", "path": "/cart" } }],
      "responses": [{
        "_rift": {
          "script": {
            "engine": "rhai",
            "code": "
              flow.delete('cart_items');
              #{ statusCode: 200, body: #{ cleared: true } }
            "
          }
        }
      }]
    }
  ]
}
```

## Real-World Scenario: Quota Exhaustion

Simulate an API with a usage quota:

```json
{
  "port": 4545,
  "_rift": {
    "flowState": { "backend": "inmemory" }
  },
  "stubs": [{
    "predicates": [{ "startsWith": { "path": "/api/" } }],
    "responses": [{
      "_rift": {
        "script": {
          "engine": "rhai",
          "code": "
            let quota = 100;
            let used = flow.get('api_calls').unwrap_or(0) + 1;
            flow.set('api_calls', used);
            let remaining = quota - used;

            if remaining < 0 {
              #{
                statusCode: 403,
                body: #{ error: 'Quota exceeded', used: used, limit: quota }
              }
            } else {
              #{
                statusCode: 200,
                headers: #{
                  'X-Quota-Remaining': `${remaining}`,
                  'X-Quota-Limit': `${quota}`
                },
                body: #{ data: 'OK', quotaRemaining: remaining }
              }
            }
          "
        }
      }
    }]
  }]
}
```

## Per-User State with Flow Keys

Use request data to isolate state per user:

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        // Get user ID from header
        let user_id = request.headers['X-User-ID'];
        let key = `cart:${user_id}`;

        let cart = flow.get(key).unwrap_or([]);
        // ... manipulate cart ...
        flow.set(key, cart);

        #{ statusCode: 200, body: cart }
      "
    }
  }
}
```

Each user has independent state.

## Circuit Breaker Pattern

```json
{
  "port": 4545,
  "_rift": {
    "flowState": { "backend": "inmemory", "ttlSeconds": 30 }
  },
  "stubs": [{
    "responses": [{
      "_rift": {
        "script": {
          "engine": "rhai",
          "code": "
            let failures = flow.get('failures').unwrap_or(0);
            let circuit_open = flow.get('circuit_open').unwrap_or(false);

            if circuit_open {
              #{ statusCode: 503, body: 'Circuit breaker open' }
            } else {
              // Simulate 20% failure rate
              if rand() < 0.2 {
                let new_failures = failures + 1;
                flow.set('failures', new_failures);

                // Open circuit after 5 failures
                if new_failures >= 5 {
                  flow.set('circuit_open', true);
                }

                #{ statusCode: 500, body: 'Service error' }
              } else {
                flow.set('failures', 0);
                #{ statusCode: 200, body: 'OK' }
              }
            }
          "
        }
      }
    }]
  }]
}
```

After 5 failures, the circuit opens for 30 seconds (TTL).

## Mountebank Cycling vs Rift Flow State

| Feature | Mountebank Cycling | Rift Flow State |
|---------|-------------------|-----------------|
| Scope | Global (shared) | Configurable (can be per-user) |
| Persistence | Memory only | In-memory or Redis |
| Reset | Restart server | TTL-based or explicit |
| Logic | Fixed sequence | Dynamic (scripted) |
| Isolation | None | Key-based |

**When to use which:**
- **Cycling**: Simple round-robin responses
- **Flow State**: Complex conditional logic, per-user state

## Best Practices

1. **Use descriptive keys**: `user:${id}:cart` not `c1`
2. **Set appropriate TTLs**: Prevent state buildup
3. **Use Redis for CI/CD**: Persist across test runs
4. **Initialize state explicitly**: Don't rely on undefined behavior
5. **Clean up in beforeEach**: Reset state between tests

## What's Next?

We've seen Rhai scripts throughout this post. Let's dive deeper into scripting:

**Next Post**: Dynamic Responses with Multi-Engine Scripting

---

*What stateful scenarios do you need to mock? Share your use cases!*

---

**Tags:** #StatefulTesting #MockServer #Rift #APITesting #FlowState
