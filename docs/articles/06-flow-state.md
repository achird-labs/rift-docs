---
title: 'Building Stateful Mock Services with Flow State'
description: 'Keep state across requests with declarative stateOps or ctx.state scripts, isolate it per caller, and inspect it through the admin API.'
audience: [developer]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
upstream:
  - repo: achird-labs/rift
    paths:
      - docs/features/flow-state.md
      - docs/features/scripting.md
verified_against:
  rift: v0.18.1
---

# Building Stateful Mock Services with Flow State

*From simple stubs to multi-step test scenarios*

---

This article is for developers whose mocks need to remember earlier requests. By the end you will
have counters, a login flow, a shopping cart and a quota built on Rift's flow state, isolated per
caller, and you will know how to inspect and reset that state from a test.

Most mock servers are stateless. Each request is independent. But real APIs have state:

- Login creates a session
- Adding items updates a cart
- Quotas track request counts
- Retries succeed after transient failures

## Understanding Flow State

Flow state is a key/value store keyed by *(flow id, key)*. Three things use it:

- **`_rift.stateOps`** writes it declaratively on an `is` response — no script needed.
- **`{{ state.<key> }}`** reads it back into a templated response (`_rift.templated: true`).
- **`ctx.state`** reads and writes it from a [script](07-scripting.md).

The imposter's `_rift.flowState` block configures the store:

```json
{
  "port": 4545,
  "protocol": "http",
  "_rift": {
    "flowState": {
      "backend": "inmemory",
      "ttlSeconds": 300,
      "flowIdSource": "header:X-User-Id"
    }
  },
  "stubs": []
}
```

| Field | Default | Meaning |
|-------|---------|---------|
| `backend` | `inmemory` | `inmemory`, or `redis` for state shared across instances |
| `ttlSeconds` | `300` | Lifetime of a key, restarted by every write to it. Must be at least `1` |
| `flowIdSource` | `imposter_port` | What a flow is: the whole imposter, or `header:<Name>` for one flow per header value |

With `flowIdSource: "header:X-User-Id"`, requests carrying `X-User-Id: alice` and
`X-User-Id: bob` see separate state — per-user isolation without building keys by hand.

For Redis, the connection settings go in a nested `redis` block:

```json
{
  "_rift": {
    "flowState": {
      "backend": "redis",
      "ttlSeconds": 600,
      "redis": { "url": "redis://localhost:6379", "poolSize": 10, "keyPrefix": "rift:" }
    }
  }
}
```

A `flowState` block Rift cannot honour — an unknown backend, an unreachable Redis, a `ttlSeconds`
below `1` — fails imposter creation with `400` rather than silently running without state. An
imposter that uses state but has no `flowState` block gets an in-memory store automatically, and
`rift-lint` reports it as `W014` so the choice is deliberate.

## A Counter Without a Script

`stateOps` runs after the response is rendered, just before it is written. Here one stub records a
visit and another reads the totals back:

```json
{
  "port": 4545,
  "protocol": "http",
  "_rift": {
    "flowState": { "backend": "inmemory", "ttlSeconds": 300 }
  },
  "stubs": [
    {
      "predicates": [{ "equals": { "method": "POST", "path": "/visits" } }],
      "responses": [{
        "is": { "statusCode": 202 },
        "_rift": {
          "stateOps": [
            { "op": "increment", "key": "visits" },
            { "op": "set", "key": "lastPage", "value": "{{ request.query.page }}" }
          ]
        }
      }]
    },
    {
      "predicates": [{ "equals": { "method": "GET", "path": "/visits" } }],
      "responses": [{
        "is": { "statusCode": 200, "body": "{{ state.visits }} visits, last page: {{ state.lastPage }}" },
        "_rift": { "templated": true }
      }]
    }
  ]
}
```

```bash
curl -X POST 'http://localhost:4545/visits?page=home'   # 202
curl -X POST 'http://localhost:4545/visits?page=cart'   # 202
curl http://localhost:4545/visits                       # 2 visits, last page: cart
```

The ops are `increment` (with an optional `by`), `set` (the value is a template), `delete` and
`clearFlow`. `stateOps` is not scripting, so it works without `--allow-injection`.

## Scripted State: Authentication Flow

When the logic branches, use a script. `ctx.state` is already bound to the request's flow, so with
`flowIdSource: "header:X-User-Id"` each user gets their own session:

```json
{
  "port": 4545,
  "protocol": "http",
  "_rift": {
    "flowState": { "backend": "inmemory", "ttlSeconds": 3600, "flowIdSource": "header:X-User-Id" }
  },
  "stubs": [
    {
      "predicates": [{ "equals": { "method": "POST", "path": "/login" } }],
      "responses": [{
        "_rift": { "script": { "engine": "rhai",
          "code": "ctx.state.set(\"session\", \"sess-\" + ctx.flowId);\nhttp(200, #{ loggedIn: true, user: ctx.flowId })" } }
      }]
    },
    {
      "predicates": [{ "equals": { "method": "GET", "path": "/profile" } }],
      "responses": [{
        "_rift": { "script": { "engine": "rhai",
          "code": "if ctx.state.exists(\"session\") {\n  http(200, #{ user: ctx.flowId, session: ctx.state.get(\"session\") })\n} else {\n  http(401, #{ error: \"not logged in\" })\n}" } }
      }]
    },
    {
      "predicates": [{ "equals": { "method": "POST", "path": "/logout" } }],
      "responses": [{
        "_rift": { "script": { "engine": "rhai",
          "code": "ctx.state.clear();\nhttp(204)" } }
      }]
    }
  ]
}
```

Start Rift with `--allow-injection`, then:

```bash
curl -H 'X-User-Id: alice' http://localhost:4545/profile          # 401 {"error":"not logged in"}
curl -H 'X-User-Id: alice' -X POST http://localhost:4545/login    # 200 {"loggedIn":true,"user":"alice"}
curl -H 'X-User-Id: alice' http://localhost:4545/profile          # 200 {"session":"sess-alice","user":"alice"}
curl -H 'X-User-Id: bob'   http://localhost:4545/profile          # 401 — bob has his own flow
curl -H 'X-User-Id: alice' -X POST http://localhost:4545/logout   # 204
curl -H 'X-User-Id: alice' http://localhost:4545/profile          # 401
```

## Scripted State: Shopping Cart

State values can be arrays and objects. The same flow settings, in JavaScript (`getOr` is the
JavaScript spelling of Rhai's `get_or`):

```json
{
  "stubs": [
    {
      "predicates": [{ "equals": { "method": "POST", "path": "/cart" } }],
      "responses": [{
        "_rift": { "script": { "engine": "javascript",
          "code": "function respond(ctx) {\n  const cart = ctx.state.getOr('cart', []);\n  cart.push(ctx.request.json);\n  ctx.state.set('cart', cart);\n  return http(201, { items: cart.length });\n}" } }
      }]
    },
    {
      "predicates": [{ "equals": { "method": "GET", "path": "/cart" } }],
      "responses": [{
        "_rift": { "script": { "engine": "javascript",
          "code": "function respond(ctx) {\n  const cart = ctx.state.getOr('cart', []);\n  const total = cart.reduce((sum, i) => sum + i.price * i.qty, 0);\n  return http(200, { items: cart, total });\n}" } }
      }]
    }
  ]
}
```

```bash
curl -H 'X-User-Id: alice' -X POST http://localhost:4545/cart -d '{"sku":"A1","price":2.5,"qty":2}'  # 201 {"items":1}
curl -H 'X-User-Id: alice' -X POST http://localhost:4545/cart -d '{"sku":"B2","price":10,"qty":1}'   # 201 {"items":2}
curl -H 'X-User-Id: alice' http://localhost:4545/cart
# {"items":[{"price":2.5,"qty":2,"sku":"A1"},{"price":10,"qty":1,"sku":"B2"}],"total":15}
```

## Scripted State: Quota Exhaustion

```json
{
  "predicates": [{ "startsWith": { "path": "/api/" } }],
  "responses": [{
    "_rift": { "script": { "engine": "rhai",
      "code": "let used = ctx.state.incr(\"calls\");\nif used > 3 {\n  http(429, #{ error: \"quota exceeded\", limit: 3 }).header(\"Retry-After\", \"60\")\n} else {\n  http(200, #{ ok: true, remaining: 3 - used })\n}" } }
  }]
}
```

The first three calls answer `200` with `remaining` counting down to `0`; the fourth answers `429`.
`incr` is atomic, so concurrent callers never double-spend the quota.

A key's TTL restarts on every write, so a counter that is written on every request never expires
while traffic keeps arriving. Reset it explicitly between tests, as below.

## Inspecting and Resetting State from Tests

The admin API reads and writes one flow's keys, which is how a test arranges state before it runs
and cleans up after:

```bash
# Read a key (404 if absent)
curl http://localhost:2525/admin/imposters/4545/flow-state/alice/calls
# {"flowId":"alice","key":"calls","value":4}

# Set a key
curl -X PUT http://localhost:2525/admin/imposters/4545/flow-state/alice/calls -d '{"value": 0}'

# Delete one key
curl -X DELETE http://localhost:2525/admin/imposters/4545/flow-state/alice/calls

# Clear the whole flow (idempotent)
curl -X DELETE http://localhost:2525/admin/imposters/4545/flow-state/alice
```

## Mountebank Cycling vs Rift Flow State

| Feature | Mountebank response cycling | Rift flow state |
|---------|-----------------------------|-----------------|
| Scope | Per stub, shared by every caller | Per flow — per imposter, or per header value |
| Persistence | Memory only | In-memory or Redis |
| Reset | Restart, or re-create the imposter | Key TTL, or the flow-state admin API |
| Logic | Fixed sequence | Declarative `stateOps`, or a script |

**When to use which:**

- **Cycling**: a fixed round-robin of responses
- **Flow state**: responses that depend on what a caller did before

## Best Practices

1. **Prefer `stateOps` when it fits**: no script, no `--allow-injection`
2. **Key flows by caller**: `flowIdSource: "header:<Name>"` isolates parallel tests
3. **Use Redis when state must be shared** across Rift instances
4. **Reset state in test setup**: `DELETE /admin/imposters/<port>/flow-state/<flow>`
5. **Configure `flowState` explicitly**: silence `W014` by making the store a choice

For the full reference — TTL rules, `cas`, `ctx.store`, `stateOps` failure semantics — see
[Flow State](https://achird-labs.github.io/rift/features/flow-state/) in the Rift docs.

## What's Next?

We've used Rhai and JavaScript scripts throughout this post. Let's dive deeper into scripting:

**Next Post**: Dynamic Responses with Rhai and JavaScript Scripting

---

**Tags:** #StatefulTesting #MockServer #Rift #APITesting #FlowState
