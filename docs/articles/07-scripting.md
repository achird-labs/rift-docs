---
title: 'Dynamic Responses with Rhai and JavaScript Scripting'
description: 'Write response logic in Rhai or JavaScript with the respond(ctx) script API, keep state in ctx.state, and test scripts before you deploy them.'
audience: [developer]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
upstream:
  - repo: achird-labs/rift
    paths:
      - docs/features/scripting.md
      - docs/features/flow-state.md
      - docs/configuration/cli.md
verified_against:
  rift: v0.18.1
---

# Dynamic Responses with Rhai and JavaScript Scripting

*One script API, two engines*

---

This article is for developers whose mocks need logic a static `is` response cannot express. By the
end you will have Rhai and JavaScript scripts answering requests, keeping state between calls, loaded
from their own files, and tested from the command line without a running server.

Static responses only get you so far. Sometimes you need:

- A response computed from the request (a query parameter, a JSON body field)
- Validation that answers `400` for bad input and `201` for good input
- Behaviour that changes over time (fail twice, then succeed)

!!! note "Not every dynamic response needs a script"
    Echoing a request field into a response is a job for response templating (`_rift.templated`),
    and bumping a counter or remembering a value is a job for declarative `_rift.stateOps` — see
    [Flow State](06-flow-state.md). Reach for a script when you need branching logic.

## The Engines

| Engine | Select with | Notes |
|--------|-------------|-------|
| **Rhai** | `"engine": "rhai"` (the default) | Compiled and cached; the fastest option |
| **JavaScript** | `"engine": "javascript"` (alias `js`) | Boa interpreter; also runs Mountebank `inject` and `decorate` functions |

Both engines are built into the released `rift` binary, and both expose the same script API. The Lua engine was
removed in Rift 0.12.0: `"engine": "lua"` is rejected when the imposter is created.

Every script surface is gated like Mountebank's `inject`, so start Rift with `--allow-injection`
(alias `--allowInjection`). Without it, creating an imposter that carries a script fails with
`400 invalid injection`.

```bash
rift --configfile imposters.json --allow-injection
```

## The Script API: `respond(ctx)`

A `_rift.script` response runs one function, `respond(ctx)`, and returns a *result constructor*
describing the response. You can write the function out in full, or leave out the wrapper and write
the body directly — the "bare-expression" form, with `ctx` already in scope.

### Rhai

```json
{
  "port": 4545,
  "protocol": "http",
  "stubs": [{
    "predicates": [{ "equals": { "path": "/hello" } }],
    "responses": [{
      "_rift": {
        "script": {
          "engine": "rhai",
          "code": "let name = ctx.request.query[\"name\"] ?? \"World\";\nhttp(200, #{ greeting: `Hello, ${name}!` })"
        }
      }
    }]
  }]
}
```

```bash
curl 'http://localhost:4545/hello?name=Ada'   # {"greeting":"Hello, Ada!"}
curl  http://localhost:4545/hello             # {"greeting":"Hello, World!"}
```

### JavaScript

The same stub in JavaScript, this time with the named `respond` function:

```json
{
  "_rift": {
    "script": {
      "engine": "javascript",
      "code": "function respond(ctx) {\n  const name = ctx.request.query.name || 'World';\n  return http(200, { greeting: `Hello, ${name}!` });\n}"
    }
  }
}
```

### What `ctx` gives you

| Field | What it is |
|-------|------------|
| `ctx.request.method`, `.path` | The request line |
| `ctx.request.query` | Query-string parameters, as a map |
| `ctx.request.headers` | Headers, with **lowercased** keys |
| `ctx.request.header(name)` | Case-insensitive header lookup |
| `ctx.request.body` | The raw body, as a string |
| `ctx.request.json` | The body parsed as JSON; unit / `null` when it is not JSON |
| `ctx.request.pathParams` | Values captured by the stub's `routePattern` |
| `ctx.state` | Key/value state for this request's flow — see [Keeping state](#keeping-state) |
| `ctx.flowId` | The flow id `ctx.state` is bound to |
| `ctx.logger` | `debug` / `info` / `warn` / `error`, written to Rift's log under target `rift::script` |

### Result constructors

| Constructor | Result |
|-------------|--------|
| `http(status)`, `http(status, body)` | That status and body. Chain `.header(name, value)` for headers |
| `delay(ms)` | Waits `ms`, then answers `200` with an empty body and an `x-rift-latency-ms` header |
| `reset()` | Resets the connection |
| `pass()`, or returning nothing | `200` with an empty body |

A map or array body is serialised as JSON with `Content-Type: application/json`; a string body is
sent as-is. A script response is script-only: `pass()` does not fall through to another response or
stub, so shape the success response with `http(...)` too. Every script response carries an
`x-rift-script: <engine>` header.

## Practical Examples

### Validate a JSON body and create a resource

```json
{
  "predicates": [{ "equals": { "method": "POST", "path": "/users" } }],
  "responses": [{
    "_rift": {
      "script": {
        "engine": "rhai",
        "code": "fn respond(ctx) {\n  let user = ctx.request.json;\n  if user == () || user.email == () {\n    return http(400, #{ error: \"email is required\" });\n  }\n  let id = ctx.state.incr(\"nextId\");\n  user.id = id;\n  http(201, user).header(\"Location\", `/users/${id}`)\n}"
      }
    }
  }]
}
```

```bash
curl -i -X POST http://localhost:4545/users -d '{"name":"Ada","email":"ada@example.com"}'
# HTTP/1.1 201 Created
# location: /users/1
# {"email":"ada@example.com","id":1,"name":"Ada"}

curl -X POST http://localhost:4545/users -d '{"name":"Bob"}'
# 400 {"error":"email is required"}
```

`ctx.request.json` is unit (`()`) when the body is missing or is not JSON, so the same check also
rejects `-d 'not json'`.

### Keeping state

`ctx.state` is a key/value store scoped to the request's *flow*. The imposter's
`_rift.flowState.flowIdSource` decides what a flow is — here, the value of an `X-Flow-Id` header, so
every caller retries independently:

```json
{
  "port": 4545,
  "protocol": "http",
  "_rift": {
    "flowState": { "backend": "inmemory", "ttlSeconds": 300, "flowIdSource": "header:X-Flow-Id" }
  },
  "stubs": [{
    "predicates": [{ "equals": { "path": "/flaky" } }],
    "responses": [{
      "_rift": {
        "script": {
          "engine": "javascript",
          "code": "function respond(ctx) {\n  const n = ctx.state.incr('attempts');\n  if (n <= 2) {\n    return http(503, { error: 'unavailable', attempt: n }).header('Retry-After', '1');\n  }\n  return http(200, { ok: true, attempt: n });\n}"
        }
      }
    }]
  }]
}
```

```bash
curl -H 'X-Flow-Id: t1' http://localhost:4545/flaky   # 503 {"attempt":1,"error":"unavailable"}
curl -H 'X-Flow-Id: t1' http://localhost:4545/flaky   # 503 {"attempt":2,"error":"unavailable"}
curl -H 'X-Flow-Id: t1' http://localhost:4545/flaky   # 200 {"attempt":3,"ok":true}
curl -H 'X-Flow-Id: t2' http://localhost:4545/flaky   # 503 {"attempt":1,"error":"unavailable"}
```

The main `ctx.state` calls are `get`, `set`, `exists`, `delete`, `incr`, `clear`, and `get_or`
(`getOr` in JavaScript). An imposter with a script but no `flowState` block still gets an in-memory
store, and `rift-lint` flags it as `W014` so the choice is deliberate. [Flow State](06-flow-state.md)
covers the store in depth.

## Keeping Scripts in Files

A JSON-escaped one-liner stops being readable after a few statements. Two ways out:

**A YAML config with a block scalar.** `--configfile` accepts YAML, whose root is a *list* of
imposters:

```yaml
- port: 4545
  protocol: http
  stubs:
    - predicates: [{ equals: { path: /inline } }]
      responses:
        - _rift:
            script:
              engine: rhai
              code: |
                let q = ctx.request.query["q"] ?? "nothing";
                http(200, "you asked for " + q)
```

**A separate script file**, referenced with `file:`, or registered once under `_rift.scripts` and
used by name with `ref:`. The engine is inferred from the extension (`.rhai` or `.js`):

```rhai
// scripts/fail-twice.rhai
fn respond(ctx) {
  let n = ctx.state.incr("attempts");
  if n <= 2 {
    http(503, #{ error: "unavailable", attempt: n }).header("Retry-After", "1")
  } else {
    http(200, #{ ok: true, attempt: n })
  }
}
```

```yaml
- port: 4545
  protocol: http
  _rift:
    flowState: { backend: inmemory, ttlSeconds: 300, flowIdSource: "header:X-Flow-Id" }
    scripts:
      failTwice:
        file: scripts/fail-twice.rhai
  stubs:
    - predicates: [{ equals: { path: /orders } }]
      responses:
        - _rift:
            script:
              ref: failTwice
```

A `file:` path in a `--configfile` resolves relative to that config file. For imposters created
through the admin API, `file:` paths resolve under `--scripts-dir`, and are rejected when that flag
is not set or when a path escapes the directory:

```bash
rift --allow-injection --scripts-dir ./scripts

curl -X POST http://localhost:2525/imposters -d '{
  "port": 4546, "protocol": "http",
  "stubs": [{ "responses": [{ "_rift": { "script": { "file": "fail-twice.rhai" } } }] }]
}'
```

## Testing Scripts Without a Server

`rift script check` validates a script file or a whole config file, and `rift script run` executes
a script against a fixture request and seeded state:

```bash
rift script check imposters.yaml
rift script check scripts/fail-twice.rhai

echo '{"method":"GET","path":"/orders"}' > req.json
rift script run scripts/fail-twice.rhai --request req.json --state attempts=2
```

```
decision: http(200) { "Content-Type": "application/json" } body="{\"attempt\":3,\"ok\":true}"
duration: 0ms
state:
  attempts = 3
logs:
  (none)
```

`check` is static: it catches syntax errors and a missing `respond` entrypoint. A script that
returns the wrong kind of value, or that references a variable that does not exist, passes `check`
and fails `run` — so `run` your scripts too.

## Errors and Limits

- A script that fails at runtime answers `500` with an `x-rift-script-error: true` header and a
  Mountebank-shaped `{"errors": [...]}` body naming the problem.
- Each script runs under a deadline, 5000 ms by default, which `_rift.scriptEngine.timeoutMs`
  changes per imposter. A script that misses it answers `504` with `x-rift-script-timeout: true`.

## Mountebank `inject` Still Works

Mountebank's JavaScript `inject` responses run unchanged on the JavaScript engine, with their own
Mountebank-shaped arguments rather than `ctx`:

```json
{
  "inject": "function (config) { return { statusCode: 200, body: 'from inject: ' + config.request.path }; }"
}
```

Keep `inject` for configs you share with Mountebank; use `_rift.script` for new Rift-only mocks.

## Upgrading Scripts Written Before 0.12

Older Rift scripts, including earlier versions of this article, used a different API. None of it
runs on current Rift:

| Old | Now |
|-----|-----|
| `"engine": "lua"` | `"engine": "rhai"` or `"javascript"` |
| `fn should_inject(request, flow_store) { … }` | `fn respond(ctx) { … }`, or a bare expression |
| `request.query.name`, `request.body` | `ctx.request.query["name"]`, `ctx.request.body` / `ctx.request.json` |
| `flow.get('k')`, `flow.set('k', v)` | `ctx.state.get("k")`, `ctx.state.set("k", v)` |
| Returning `#{ statusCode: 200, body: … }` | Returning `http(200, …)` |

`rift script check` reports a `should_inject`-only script as having no `respond` entrypoint, and
`rift script run` reports a script that still returns a map.

## Choosing an Engine

**Use Rhai when** throughput matters or you want the default: it is compiled and cached.

**Use JavaScript when** your team knows it, or you are carrying Mountebank `inject` and `decorate`
functions across.

**Use neither when** templating or `stateOps` can express the behaviour — a declarative response is
easier to read and needs no `--allow-injection`.

For the full reference — `ctx.store`, `cas`, TTLs, engine selection order — see
[Scripting](https://achird-labs.github.io/rift/features/scripting/) in the Rift docs.

## What's Next?

Scripts are powerful for generating responses. But what about capturing real API behavior?

**Next Post**: Recording and Replaying API Traffic with Proxy Mode

---

**Tags:** #Scripting #Rhai #JavaScript #MockServer #Rift #DynamicResponses
