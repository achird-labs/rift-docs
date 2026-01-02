---
layout: default
title: 'Production-Ready Mocking: Docker, Kubernetes, and CI/CD'
---

# Production-Ready Mocking: Docker, Kubernetes, and CI/CD

*Deploy mock services like a pro*

---

You've built amazing mocks with Rift. Now let's deploy them properly:
- Docker containers for consistency
- Kubernetes for scalability
- CI/CD pipelines for automation
- Observability for debugging

Let's make your mocks production-ready.

## Docker Deployment

### Basic Docker Run

```bash
docker run -p 2525:2525 -p 4545-4555:4545-4555 \
  ghcr.io/etacassiopeia/rift-proxy:latest
```

### With Configuration File

```bash
docker run -p 2525:2525 -p 4545:4545 \
  -v $(pwd)/imposters.json:/imposters.json \
  ghcr.io/etacassiopeia/rift-proxy:latest \
  --configfile /imposters.json
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  rift:
    image: ghcr.io/etacassiopeia/rift-proxy:latest
    ports:
      - "2525:2525"      # Admin API
      - "4545-4555:4545-4555"  # Imposter ports
    volumes:
      - ./imposters:/imposters:ro
    command: --configfile /imposters/services.json --allow-injection
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2525/"]
      interval: 10s
      timeout: 5s
      retries: 3
    environment:
      - RUST_LOG=info
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.5'
```

### Multi-Service Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  user-service-mock:
    image: ghcr.io/etacassiopeia/rift-proxy:latest
    ports:
      - "4545:4545"
    volumes:
      - ./mocks/users.json:/config.json:ro
    command: --configfile /config.json

  order-service-mock:
    image: ghcr.io/etacassiopeia/rift-proxy:latest
    ports:
      - "4546:4546"
    volumes:
      - ./mocks/orders.json:/config.json:ro
    command: --configfile /config.json

  payment-service-mock:
    image: ghcr.io/etacassiopeia/rift-proxy:latest
    ports:
      - "4547:4547"
    volumes:
      - ./mocks/payments.json:/config.json:ro
    command: --configfile /config.json

  # Your application under test
  app:
    build: .
    depends_on:
      - user-service-mock
      - order-service-mock
      - payment-service-mock
    environment:
      - USER_SERVICE_URL=http://user-service-mock:4545
      - ORDER_SERVICE_URL=http://order-service-mock:4546
      - PAYMENT_SERVICE_URL=http://payment-service-mock:4547
```

## Kubernetes Deployment

### Basic Deployment

```yaml
# rift-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rift-mock-server
  labels:
    app: rift
spec:
  replicas: 2
  selector:
    matchLabels:
      app: rift
  template:
    metadata:
      labels:
        app: rift
    spec:
      containers:
        - name: rift
          image: ghcr.io/etacassiopeia/rift-proxy:latest
          ports:
            - containerPort: 2525
              name: admin
            - containerPort: 4545
              name: mock
          args:
            - --configfile
            - /config/imposters.json
          volumeMounts:
            - name: config
              mountPath: /config
          resources:
            limits:
              memory: "128Mi"
              cpu: "500m"
            requests:
              memory: "64Mi"
              cpu: "100m"
          livenessProbe:
            httpGet:
              path: /
              port: 2525
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 2525
            initialDelaySeconds: 3
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: rift-config
---
apiVersion: v1
kind: Service
metadata:
  name: rift-mock-server
spec:
  selector:
    app: rift
  ports:
    - name: admin
      port: 2525
      targetPort: 2525
    - name: mock
      port: 4545
      targetPort: 4545
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: rift-config
data:
  imposters.json: |
    {
      "imposters": [
        {
          "port": 4545,
          "protocol": "http",
          "name": "User Service Mock",
          "stubs": [
            {
              "predicates": [{ "equals": { "path": "/health" } }],
              "responses": [{ "is": { "statusCode": 200, "body": "OK" } }]
            }
          ]
        }
      ]
    }
```

### With Persistent State (Redis)

```yaml
# rift-with-redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rift-stateful
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: rift
          image: ghcr.io/etacassiopeia/rift-proxy:latest
          # ... other config ...
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector:
    app: redis
  ports:
    - port: 6379
```

Configuration with Redis:

```json
{
  "port": 4545,
  "_rift": {
    "flowState": {
      "backend": "redis",
      "redis": {
        "url": "redis://redis:6379",
        "keyPrefix": "rift:prod:"
      }
    }
  }
}
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rift-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rift-mock-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests with Rift

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      rift:
        image: ghcr.io/etacassiopeia/rift-proxy:latest
        ports:
          - 2525:2525
          - 4545:4545
        options: >-
          --health-cmd "curl -f http://localhost:2525/"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Load mock configuration
        run: |
          curl -X POST http://localhost:2525/imposters \
            -H "Content-Type: application/json" \
            -d @./test/fixtures/imposters.json

      - name: Run tests
        run: npm test
        env:
          API_URL: http://localhost:4545

      - name: Verify mock usage
        run: |
          # Check that expected endpoints were called
          curl http://localhost:2525/imposters/4545 | jq '.requests | length'
```

### GitLab CI

```yaml
# .gitlab-ci.yml
test:
  image: node:20
  services:
    - name: ghcr.io/etacassiopeia/rift-proxy:latest
      alias: rift
  variables:
    API_URL: http://rift:4545
  before_script:
    - |
      # Wait for Rift to be ready
      for i in {1..30}; do
        curl -s http://rift:2525/ && break
        sleep 1
      done
    - |
      # Load configuration
      curl -X POST http://rift:2525/imposters \
        -H "Content-Type: application/json" \
        -d @./fixtures/mocks.json
  script:
    - npm ci
    - npm test
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any

    stages {
        stage('Start Mocks') {
            steps {
                sh '''
                    docker run -d --name rift-mocks \
                        -p 2525:2525 -p 4545:4545 \
                        -v ${WORKSPACE}/fixtures:/fixtures \
                        ghcr.io/etacassiopeia/rift-proxy:latest \
                        --configfile /fixtures/mocks.json

                    # Wait for startup
                    sleep 5
                '''
            }
        }

        stage('Test') {
            environment {
                API_URL = 'http://localhost:4545'
            }
            steps {
                sh 'npm test'
            }
        }
    }

    post {
        always {
            sh 'docker rm -f rift-mocks || true'
        }
    }
}
```

## Observability

### Prometheus Metrics

Rift exposes metrics on port 9090:

```bash
curl http://localhost:9090/metrics
```

Available metrics:

```
# Request counts
rift_requests_total{port="4545",method="GET",path="/api/users",status="200"}

# Latency histogram
rift_request_duration_seconds_bucket{port="4545",le="0.1"}

# Fault injection stats
rift_fault_injections_total{type="latency"}
rift_fault_injections_total{type="error"}

# Flow state operations
rift_flow_state_operations_total{operation="get"}
rift_flow_state_operations_total{operation="set"}
```

### Grafana Dashboard

```yaml
# kubernetes/grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rift-dashboard
data:
  rift-dashboard.json: |
    {
      "title": "Rift Mock Server",
      "panels": [
        {
          "title": "Request Rate",
          "type": "graph",
          "targets": [{
            "expr": "rate(rift_requests_total[5m])"
          }]
        },
        {
          "title": "Latency P99",
          "type": "graph",
          "targets": [{
            "expr": "histogram_quantile(0.99, rate(rift_request_duration_seconds_bucket[5m]))"
          }]
        }
      ]
    }
```

### Logging

```bash
# Set log level
docker run -e RUST_LOG=debug ghcr.io/etacassiopeia/rift-proxy:latest

# Log levels: error, warn, info, debug, trace
```

Structured JSON logging:

```bash
docker run -e RUST_LOG=info ghcr.io/etacassiopeia/rift-proxy:latest 2>&1 | jq
```

## Configuration Validation

### Pre-deployment Linting

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
          docker run --rm \
            -v ${{ github.workspace }}/fixtures:/fixtures \
            ghcr.io/etacassiopeia/rift-lint /fixtures --strict

      - name: Validate configuration loads
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/fixtures:/fixtures \
            ghcr.io/etacassiopeia/rift-proxy:latest \
            --configfile /fixtures/mocks.json --dry-run
```

## Resource Optimization

### Memory Usage

Rift is significantly lighter than Mountebank:

| Server | Idle Memory | 10 Imposters | 100 Imposters |
|--------|-------------|--------------|---------------|
| Mountebank | ~180MB | ~220MB | ~350MB |
| Rift | ~15MB | ~20MB | ~40MB |

### Container Sizing

```yaml
# Recommended resource limits
resources:
  requests:
    memory: "32Mi"
    cpu: "50m"
  limits:
    memory: "128Mi"
    cpu: "500m"
```

### Startup Time

| Server | Cold Start | With 10 Imposters |
|--------|------------|-------------------|
| Mountebank | ~3-5s | ~5-8s |
| Rift | ~0.3s | ~0.5s |

## Security Considerations

### Network Policies (Kubernetes)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rift-network-policy
spec:
  podSelector:
    matchLabels:
      app: rift
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: test-runner
      ports:
        - port: 2525
        - port: 4545
```

### Disable Injection in Production

```bash
# Don't use --allow-injection in shared environments
docker run ghcr.io/etacassiopeia/rift-proxy:latest \
  --configfile /config.json
  # No --allow-injection flag
```

## What's Next?

Your mocks are deployed. Let's ensure they're correct:

**Next Post**: Quality Assurance with rift-verify and rift-lint

---

*How do you deploy mock services in your infrastructure? Share your setup!*

---

**Tags:** #Docker #Kubernetes #CICD #DevOps #MockServer #Rift #Deployment
