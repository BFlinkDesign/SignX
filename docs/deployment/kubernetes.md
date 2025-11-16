# Kubernetes Deployment Guide

Complete guide for deploying on Kubernetes.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm (optional, for charts)
- Ingress controller

## Quick Start

```bash
# Create namespace
kubectl create namespace apex

# Apply manifests
kubectl apply -f infra/k8s/ -n apex

# Check status
kubectl get pods -n apex
```

## Manifests Structure

```
infra/k8s/
├── namespace.yaml
├── secrets.yaml
├── configmap.yaml
├── api/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── worker/
│   ├── deployment.yaml
│   └── service.yaml
└── postgres/
    ├── statefulset.yaml
    └── service.yaml
```

## Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: apex
```

## Secrets

### Create Secrets

```bash
# From .env file
kubectl create secret generic apex-secrets \
  --from-env-file=.env.prod \
  -n apex

# Or manually
kubectl create secret generic apex-secrets \
  --from-literal=APEX_DATABASE_URL=postgresql://... \
  --from-literal=APEX_REDIS_URL=redis://... \
  -n apex
```

### Secrets Manifest

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: apex-secrets
  namespace: apex
type: Opaque
stringData:
  APEX_DATABASE_URL: postgresql://user:pass@db:5432/apex
  APEX_MINIO_ACCESS_KEY: minioadmin
  APEX_MINIO_SECRET_KEY: minioadmin
```

## ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: apex-config
  namespace: apex
data:
  APEX_ENV: "prod"
  APEX_SERVICE_NAME: "api"
  APEX_RATE_LIMIT_PER_MIN: "100"
```

## API Deployment

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-api
  namespace: apex
spec:
  replicas: 2
  selector:
    matchLabels:
      app: apex-api
  template:
    metadata:
      labels:
        app: apex-api
    spec:
      containers:
      - name: api
        image: registry.example.com/apex-api:v0.1.0
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: apex-secrets
        - configMapRef:
            name: apex-config
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: apex-api
  namespace: apex
spec:
  selector:
    app: apex-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apex-api
  namespace: apex
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: apex-api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: apex-api
            port:
              number: 80
```

## Worker Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-worker
  namespace: apex
spec:
  replicas: 3
  selector:
    matchLabels:
      app: apex-worker
  template:
    metadata:
      labels:
        app: apex-worker
    spec:
      containers:
      - name: worker
        image: registry.example.com/apex-worker:v0.1.0
        envFrom:
        - secretRef:
            name: apex-secrets
        command: ["celery", "-A", "apex.worker.app", "worker", "--loglevel=info"]
        resources:
          requests:
            memory: "128Mi"
            cpu: "250m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

## Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: apex-api-hpa
  namespace: apex
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: apex-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Persistent Volumes

### PostgreSQL

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: apex
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
```

### MinIO

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-pvc
  namespace: apex
spec:
  accessModes:
  - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
```

## Service Mesh (Optional)

### Istio Configuration

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: apex-api
  namespace: apex
spec:
  hosts:
  - api.example.com
  http:
  - route:
    - destination:
        host: apex-api
        port:
          number: 80
```

## Monitoring Integration

### ServiceMonitor (Prometheus Operator)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: apex-api
  namespace: apex
spec:
  selector:
    matchLabels:
      app: apex-api
  endpoints:
  - port: http
    path: /metrics
    interval: 15s
```

## Deployment Strategies

### Rolling Update

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

### Blue-Green

```bash
# Deploy new version with different label
kubectl set image deployment/apex-api api=registry.example.com/apex-api:v0.2.0

# Switch traffic
kubectl patch service apex-api -p '{"spec":{"selector":{"version":"v0.2.0"}}}'
```

## Next Steps

- [**Production Deployment**](production.md) - Complete production guide
- [**Monitoring Guide**](../operations/monitoring.md) - Metrics setup

