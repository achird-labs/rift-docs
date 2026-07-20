---
layout: default
title: 'Dynamic Responses with Multi-Engine Scripting'
---

# Dynamic Responses with Multi-Engine Scripting

*Choose your language: Rhai, Lua, or JavaScript*

---

Static responses only get you so far. Sometimes you need:
- Dynamic data based on request content
- Computed values (timestamps, UUIDs)
- Conditional logic
- Request transformation

Rift supports three scripting engines, each with its strengths. Let's explore them all.

## The Scripting Engines

| Engine | Built-in | Sandboxed | Performance | Syntax |
|--------|----------|-----------|-------------|--------|
| **Rhai** | Yes | Yes | Excellent | Rust-like |
| **Lua** | Feature flag | Yes | Excellent | Simple |
| **JavaScript** | Feature flag | No | Good | Familiar |

### Enabling Engines

Rhai is always available. For Lua and JavaScript:

```bash
# Build with all engines
cargo build --release --features "lua javascript"

# Or with Docker (pre-built with all engines)
docker pull zainalpour/rift-proxy:latest
```

## Rhai: The Default Choice

Rhai is a safe, fast scripting language designed for embedding. Its syntax resembles Rust.

### Basic Response

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "#{ statusCode: 200, body: 'Hello from Rhai!' }"
    }
  }
}
```

### Using Request Data

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        let name = request.query.name;
        let greeting = if name.is_empty() { 'World' } else { name };
        #{
          statusCode: 200,
          body: `Hello, ${greeting}!`
        }
      "
    }
  }
}
```

### Working with JSON Bodies

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        let body = parse_json(request.body);
        let user_id = body.userId;
        let action = body.action;

        #{
          statusCode: 200,
          body: #{
            processed: true,
            userId: user_id,
            action: action,
            timestamp: timestamp()
          }
        }
      "
    }
  }
}
```

### Conditional Responses

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        let auth = request.headers['Authorization'];

        if auth.is_empty() {
          #{ statusCode: 401, body: 'Unauthorized' }
        } else if auth.starts_with('Bearer ') {
          #{ statusCode: 200, body: 'Authenticated' }
        } else {
          #{ statusCode: 400, body: 'Invalid auth format' }
        }
      "
    }
  }
}
```

### Flow State in Rhai

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        let count = flow.get('count').unwrap_or(0) + 1;
        flow.set('count', count);

        #{
          statusCode: 200,
          body: #{ requestNumber: count }
        }
      "
    }
  }
}
```

### Rhai Built-in Functions

| Function | Description | Example |
|----------|-------------|---------|
| `timestamp()` | Unix timestamp (ms) | `1704067200000` |
| `uuid()` | Random UUID | `"550e8400-..."` |
| `parse_json(s)` | Parse JSON string | `parse_json(request.body)` |
| `to_json(obj)` | Stringify to JSON | `to_json(#{ a: 1 })` |
| `rand()` | Random 0.0-1.0 | `0.42` |
| `rand_int(min, max)` | Random integer | `rand_int(1, 100)` |

## Lua: Simple and Fast

Lua is lightweight and easy to learn. Great for teams familiar with it.

### Basic Response

```json
{
  "_rift": {
    "script": {
      "engine": "lua",
      "code": "return { statusCode = 200, body = 'Hello from Lua!' }"
    }
  }
}
```

### Using Request Data

```json
{
  "_rift": {
    "script": {
      "engine": "lua",
      "code": "
        local name = request.query.name or 'World'
        return {
          statusCode = 200,
          headers = { ['Content-Type'] = 'text/plain' },
          body = 'Hello, ' .. name .. '!'
        }
      "
    }
  }
}
```

### Working with JSON

```json
{
  "_rift": {
    "script": {
      "engine": "lua",
      "code": "
        local json = require('json')
        local body = json.decode(request.body)

        return {
          statusCode = 200,
          body = json.encode({
            received = body,
            processed = true
          })
        }
      "
    }
  }
}
```

### Flow State in Lua

```json
{
  "_rift": {
    "script": {
      "engine": "lua",
      "code": "
        local count = flow:get('count') or 0
        count = count + 1
        flow:set('count', count)

        return {
          statusCode = 200,
          body = 'Count: ' .. count
        }
      "
    }
  }
}
```

### Lua Advantages

- Simple syntax
- Excellent for string manipulation
- Lightweight runtime
- Great documentation

## JavaScript: Familiar Syntax

JavaScript uses the same syntax as Mountebank's `inject`. Easiest migration path.

### Basic Response

```json
{
  "_rift": {
    "script": {
      "engine": "javascript",
      "code": "return { statusCode: 200, body: 'Hello from JS!' };"
    }
  }
}
```

### Using Request Data

```json
{
  "_rift": {
    "script": {
      "engine": "javascript",
      "code": "
        const name = request.query.name || 'World';
        return {
          statusCode: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ greeting: `Hello, ${name}!` })
        };
      "
    }
  }
}
```

### Flow State in JavaScript

```json
{
  "_rift": {
    "script": {
      "engine": "javascript",
      "code": "
        const count = (flow.get('count') || 0) + 1;
        flow.set('count', count);

        return {
          statusCode: 200,
          body: JSON.stringify({ count })
        };
      "
    }
  }
}
```

### Mountebank `inject` Compatibility

Mountebank's inject format works with the `inject` response type:

```json
{
  "inject": "function(request, state, logger) { return { statusCode: 200, body: 'Hello' }; }"
}
```

This uses the JavaScript engine under the hood.

## Request Object Reference

Available in all engines:

```javascript
request = {
  method: "POST",
  path: "/api/users",
  query: { page: "1", limit: "10" },
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer token123"
  },
  body: "{\"name\": \"Alice\"}"
}
```

## Response Object Reference

Return this structure:

```javascript
{
  statusCode: 200,           // Required
  headers: {                 // Optional
    "Content-Type": "application/json"
  },
  body: "response body"      // Optional (string or object)
}
```

## Practical Examples

### Echo Service

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        #{
          statusCode: 200,
          headers: #{ 'Content-Type': 'application/json' },
          body: #{
            method: request.method,
            path: request.path,
            query: request.query,
            headers: request.headers,
            body: request.body,
            timestamp: timestamp()
          }
        }
      "
    }
  }
}
```

### ID Generator

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        let body = parse_json(request.body);
        body.id = uuid();
        body.createdAt = timestamp();

        #{
          statusCode: 201,
          headers: #{ 'Location': `/resources/${body.id}` },
          body: body
        }
      "
    }
  }
}
```

### Request Validator

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        let body = parse_json(request.body);
        let errors = [];

        if body.email.is_empty() {
          errors.push('email is required');
        }
        if body.name.is_empty() {
          errors.push('name is required');
        }
        if body.age < 0 || body.age > 150 {
          errors.push('age must be between 0 and 150');
        }

        if errors.len() > 0 {
          #{
            statusCode: 400,
            body: #{ errors: errors, valid: false }
          }
        } else {
          #{
            statusCode: 200,
            body: #{ valid: true, data: body }
          }
        }
      "
    }
  }
}
```

### Dynamic Routing

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        let parts = request.path.split('/');
        let resource = parts[2];  // /api/{resource}/...
        let id = if parts.len() > 3 { parts[3] } else { '' };

        switch resource {
          'users' => #{
            statusCode: 200,
            body: #{ type: 'user', id: id, name: 'Alice' }
          },
          'orders' => #{
            statusCode: 200,
            body: #{ type: 'order', id: id, total: 99.99 }
          },
          _ => #{
            statusCode: 404,
            body: #{ error: `Unknown resource: ${resource}` }
          }
        }
      "
    }
  }
}
```

## Performance Comparison

| Engine | Simple Response | Complex Logic | JSON Processing |
|--------|----------------|---------------|-----------------|
| Rhai | ~0.1ms | ~0.3ms | ~0.5ms |
| Lua | ~0.1ms | ~0.2ms | ~0.4ms |
| JavaScript | ~0.5ms | ~1.0ms | ~1.5ms |

Rhai and Lua are significantly faster for high-throughput scenarios.

## Choosing an Engine

**Use Rhai when:**
- Performance matters
- You want sandboxed execution
- You're comfortable with Rust-like syntax

**Use Lua when:**
- Team knows Lua
- Simple scripting needs
- Maximum performance required

**Use JavaScript when:**
- Migrating from Mountebank
- Team prefers JS syntax
- Using complex logic (JS has richer stdlib)

## Error Handling

Scripts that throw errors return 500:

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        // This will error and return 500
        let x = undefined_variable;
      "
    }
  }
}
```

Handle errors gracefully:

```json
{
  "_rift": {
    "script": {
      "engine": "rhai",
      "code": "
        try {
          let body = parse_json(request.body);
          #{ statusCode: 200, body: body }
        } catch (err) {
          #{ statusCode: 400, body: #{ error: 'Invalid JSON' } }
        }
      "
    }
  }
}
```

## What's Next?

Scripts are powerful for generating responses. But what about capturing real API behavior?

**Next Post**: Recording and Replaying API Traffic with Proxy Mode

---

*Which scripting engine do you prefer? Share your use cases in the comments!*

---

**Tags:** #Scripting #Rhai #Lua #JavaScript #MockServer #Rift #DynamicResponses
