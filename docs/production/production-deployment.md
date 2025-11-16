# Production Deployment Guide

Complete guide for deploying SIGN X Studio Clone to production environments.

## Table of Contents

1. [Overview](#overview)
2. [Multi-Environment Strategy](#multi-environment-strategy)
3. [Infrastructure as Code](#infrastructure-as-code)
4. [Container Orchestration](#container-orchestration)
5. [Blue-Green Deployment](#blue-green-deployment)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Domain & DNS Setup](#domain--dns-setup)
8. [Secrets Management](#secrets-management)
9. [Environment Variables](#environment-variables)
10. [Validation & Testing](#validation--testing)

## Overview

This guide covers production deployment for SIGN X Studio Clone using industry-standard practices:

- **Infrastructure as Code**: Terraform for AWS/GCP
- **Container Orchestration**: Kubernetes with Helm
- **Deployment Strategy**: Blue-green with automated rollback
- **Security**: TLS termination, secrets management, encryption
- **Monitoring**: Distributed tracing, log aggregation, alerting

## Multi-Environment Strategy

### Environment Hierarchy

```
Production (prod)
    ↓
Staging (staging)
    ↓
Development (dev)
```

### Environment Characteristics

| Environment | Purpose | Database | Replicas | Monitoring |
|-------------|---------|----------|----------|------------|
| **dev** | Local development | Local PostgreSQL | 1 | Basic |
| **staging** | Pre-production testing | Staging DB (full data) | 2 | Full |
| **prod** | Production traffic | Production DB (multi-region) | 3+ | Full + PagerDuty |

### Environment-Specific Configurations

#### Development

```yaml
# infra/terraform/dev/main.tf
module "apex_dev" {
  source = "../modules/apex"
  
  environment = "dev"
  instance_type = "t3.medium"
  min_instances = 1
  max_instances = 2
  
  database_instance = "db.t3.micro"
  enable_backups = false
  enable_monitoring = false
}
```

#### Staging

```yaml
# infra/terraform/staging/main.tf
module "apex_staging" {
  source = "../modules/apex"
  
  environment = "staging"
  instance_type = "t3.large"
  min_instances = 2
  max_instances = 4
  
  database_instance = "db.t3.small"
  enable_backups = true
  backup_retention_days = 7
  enable_monitoring = true
  enable_alerts = true
}
```

#### Production

```yaml
# infra/terraform/prod/main.tf
module "apex_prod" {
  source = "../modules/apex"
  
  environment = "prod"
  instance_type = "t3.xlarge"
  min_instances = 3
  max_instances = 10
  
  database_instance = "db.r5.large"
  database_multi_az = true
  enable_backups = true
  backup_retention_days = 30
  enable_monitoring = true
  enable_alerts = true
  enable_pagerduty = true
  
  # High availability
  multi_region = true
  region_primary = "us-east-1"
  region_secondary = "us-west-2"
}
```

## Infrastructure as Code

### Terraform Setup

#### Project Structure

```
infra/terraform/
├── modules/
│   └── apex/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       ├── vpc.tf
│       ├── rds.tf
│       ├── eks.tf
│       ├── redis.tf
│       └── s3.tf
├── dev/
│   ├── main.tf
│   ├── terraform.tfvars
│   └── backend.tf
├── staging/
│   ├── main.tf
│   ├── terraform.tfvars
│   └── backend.tf
└── prod/
    ├── main.tf
    ├── terraform.tfvars
    └── backend.tf
```

#### Terraform Module (AWS)

```hcl
# infra/terraform/modules/apex/vpc.tf
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-apex-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone   = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.environment}-apex-private-${count.index + 1}"
  }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.environment}-apex-public-${count.index + 1}"
  }
}
```

#### RDS Configuration

```hcl
# infra/terraform/modules/apex/rds.tf
resource "aws_db_instance" "postgres" {
  identifier = "${var.environment}-apex-db"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.database_instance

  allocated_storage     = var.database_storage
  max_allocated_storage = var.database_storage_max
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "apex"
  username = "apex_admin"
  password = var.database_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = var.backup_retention_days
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  multi_az               = var.database_multi_az
  publicly_accessible    = false
  skip_final_snapshot    = var.environment == "dev"
  final_snapshot_identifier = "${var.environment}-apex-final-snapshot"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  performance_insights_enabled = var.environment == "prod"
  monitoring_interval          = var.environment == "prod" ? 60 : 0
  monitoring_role_arn         = var.environment == "prod" ? aws_iam_role.rds_monitoring.arn : null

  tags = {
    Name        = "${var.environment}-apex-db"
    Environment = var.environment
  }
}
```

#### ElastiCache (Redis)

```hcl
# infra/terraform/modules/apex/redis.tf
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.environment}-apex-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.environment}-apex-redis"
  description                = "Redis for APEX ${var.environment}"

  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = var.redis_node_type
  num_cache_clusters         = var.redis_num_nodes

  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.main.name

  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.redis.id]

  at_rest_encryption_enabled  = true
  transit_encryption_enabled = var.environment == "prod"

  automatic_failover_enabled = var.environment == "prod"
  multi_az_enabled          = var.environment == "prod"

  snapshot_retention_limit   = var.environment == "prod" ? 7 : 1
  snapshot_window            = "03:00-05:00"

  tags = {
    Name        = "${var.environment}-apex-redis"
    Environment = var.environment
  }
}
```

#### S3 (MinIO Alternative)

```hcl
# infra/terraform/modules/apex/s3.tf
resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.environment}-apex-artifacts"

  tags = {
    Name        = "${var.environment}-apex-artifacts"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  rule {
    id     = "archive-old-objects"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
}
```

#### EKS Cluster

```hcl
# infra/terraform/modules/apex/eks.tf
resource "aws_eks_cluster" "main" {
  name     = "${var.environment}-apex"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.28"

  vpc_config {
    subnet_ids              = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_access_cidrs
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_cloudwatch_log_group.eks_cluster,
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]

  tags = {
    Name        = "${var.environment}-apex-eks"
    Environment = var.environment
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.private[*].id

  scaling_config {
    desired_size = var.min_instances
    max_size     = var.max_instances
    min_size     = var.min_instances
  }

  instance_types = [var.instance_type]

  labels = {
    Environment = var.environment
  }

  tags = {
    Name        = "${var.environment}-apex-node"
    Environment = var.environment
  }
}
```

### GCP Alternative

For GCP deployments, see `infra/terraform/gcp/` directory with equivalent configurations using:
- Google Cloud SQL (PostgreSQL)
- Memorystore (Redis)
- Cloud Storage (S3 alternative)
- GKE (Kubernetes)

## Container Orchestration

### Kubernetes Manifests

#### Namespace

```yaml
# k8s/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: apex
  labels:
    name: apex
    environment: production
```

#### ConfigMap

```yaml
# k8s/base/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: apex-config
  namespace: apex
data:
  APEX_ENV: "prod"
  APEX_SERVICE_NAME: "api"
  APEX_APP_VERSION: "0.1.0"
  APEX_RATE_LIMIT_PER_MIN: "100"
  APEX_BODY_SIZE_LIMIT_BYTES: "256000"
  APEX_CORS_ALLOW_ORIGINS: "https://app.example.com,https://admin.example.com"
```

#### Secrets (from Vault)

```yaml
# k8s/base/secrets.yaml (reference only - actual secrets from Vault)
apiVersion: v1
kind: Secret
metadata:
  name: apex-secrets
  namespace: apex
type: Opaque
data:
  # Values injected via external-secrets operator
  # See: infra/k8s/external-secrets/
```

### Helm Chart

#### Chart Structure

```
k8s/charts/apex/
├── Chart.yaml
├── values.yaml
├── values-prod.yaml
├── values-staging.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   └── configmap.yaml
└── templates/tests/
    └── test-connection.yaml
```

#### Chart.yaml

```yaml
# k8s/charts/apex/Chart.yaml
apiVersion: v2
name: apex
description: SIGN X Studio Clone Helm Chart
type: application
version: 0.1.0
appVersion: "0.1.0"
dependencies:
  - name: postgresql
    version: 12.0.0
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: redis
    version: 17.0.0
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
```

#### Values (Production)

```yaml
# k8s/charts/apex/values-prod.yaml
replicaCount: 3

image:
  repository: registry.example.com/apex-api
  tag: "v0.1.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: apex-api-tls
      hosts:
        - api.example.com

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "2000m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

podDisruptionBudget:
  enabled: true
  minAvailable: 2

nodeSelector:
  node-type: compute

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values:
                  - apex-api
          topologyKey: kubernetes.io/hostname

tolerations: []
```

#### Deployment Template

```yaml
# k8s/charts/apex/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "apex.fullname" . }}-api
  namespace: {{ .Values.namespace }}
  labels:
    {{- include "apex.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      {{- include "apex.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
      labels:
        {{- include "apex.selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "apex.serviceAccountName" . }}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8000
              protocol: TCP
          envFrom:
            - configMapRef:
                name: {{ include "apex.fullname" . }}-config
            - secretRef:
                name: {{ include "apex.fullname" . }}-secrets
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          livenessProbe:
            {{- toYaml .Values.livenessProbe | nindent 12 }}
          readinessProbe:
            {{- toYaml .Values.readinessProbe | nindent 12 }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

## Blue-Green Deployment

### Strategy Overview

Blue-green deployment ensures zero-downtime deployments:

1. **Blue**: Current production (active)
2. **Green**: New version (standby)
3. **Switch**: Traffic routed to Green
4. **Rollback**: If issues, route back to Blue

### Implementation

#### Kubernetes Service with Selectors

```yaml
# k8s/base/service-blue.yaml
apiVersion: v1
kind: Service
metadata:
  name: apex-api-blue
  namespace: apex
spec:
  selector:
    app: apex-api
    version: blue
  ports:
    - port: 80
      targetPort: 8000
---
# k8s/base/service-green.yaml
apiVersion: v1
kind: Service
metadata:
  name: apex-api-green
  namespace: apex
spec:
  selector:
    app: apex-api
    version: green
  ports:
    - port: 80
      targetPort: 8000
```

#### Ingress with Weighted Routing

```yaml
# k8s/base/ingress-weighted.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apex-api
  namespace: apex
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "0"  # 0% to green initially
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: apex-api-blue
                port:
                  number: 80
```

### Deployment Script

```bash
#!/bin/bash
# scripts/deploy-blue-green.sh

set -e

CURRENT_VERSION=$(kubectl get deployment apex-api -n apex -o jsonpath='{.spec.template.metadata.labels.version}')
NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

echo "Current version: $CURRENT_VERSION"
echo "Deploying version: $NEW_VERSION"

# Determine blue/green
if [ "$CURRENT_VERSION" == "blue" ]; then
  DEPLOY_TO="green"
  ACTIVE="blue"
else
  DEPLOY_TO="blue"
  ACTIVE="green"
fi

# Deploy new version
echo "Deploying to $DEPLOY_TO..."
kubectl set image deployment/apex-api-$DEPLOY_TO api=registry.example.com/apex-api:$NEW_VERSION -n apex
kubectl rollout status deployment/apex-api-$DEPLOY_TO -n apex --timeout=5m

# Health check
echo "Running health checks..."
for i in {1..10}; do
  if kubectl exec -n apex deployment/apex-api-$DEPLOY_TO -- curl -f http://localhost:8000/health; then
    echo "Health check passed"
    break
  fi
  sleep 10
done

# Gradual traffic shift (10% increments)
for weight in 10 25 50 75 100; do
  echo "Shifting $weight% traffic to $DEPLOY_TO..."
  kubectl annotate ingress apex-api -n apex \
    nginx.ingress.kubernetes.io/canary-weight="$weight" --overwrite
  
  # Wait and verify
  sleep 30
  ERROR_RATE=$(kubectl logs -n apex deployment/apex-api-$DEPLOY_TO --tail=100 | grep -c "ERROR" || true)
  if [ "$ERROR_RATE" -gt 5 ]; then
    echo "High error rate detected, rolling back..."
    kubectl annotate ingress apex-api -n apex \
      nginx.ingress.kubernetes.io/canary-weight="0" --overwrite
    exit 1
  fi
done

# Final verification
echo "Final verification..."
sleep 60
if kubectl logs -n apex deployment/apex-api-$DEPLOY_TO --tail=1000 | grep -q "ERROR"; then
  echo "Errors detected after full rollout, rolling back..."
  kubectl annotate ingress apex-api -n apex \
    nginx.ingress.kubernetes.io/canary-weight="0" --overwrite
  exit 1
fi

echo "Deployment successful!"
echo "New version $NEW_VERSION is live on $DEPLOY_TO"
```

### Automated Rollback

```yaml
# k8s/base/rollback-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: apex-api-rollback
  namespace: apex
spec:
  template:
    spec:
      containers:
        - name: rollback
          image: bitnami/kubectl:latest
          command:
            - /bin/sh
            - -c
            - |
              # Check error rate
              ERROR_COUNT=$(kubectl logs -n apex deployment/apex-api-green --tail=1000 | grep -c "ERROR" || echo "0")
              
              if [ "$ERROR_COUNT" -gt 10 ]; then
                echo "High error rate detected, rolling back to blue"
                kubectl annotate ingress apex-api -n apex \
                  nginx.ingress.kubernetes.io/canary-weight="0" --overwrite
              fi
      restartPolicy: Never
```

## SSL/TLS Configuration

### Let's Encrypt with cert-manager

#### Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

#### ClusterIssuer

```yaml
# k8s/base/cert-manager-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

#### Certificate

```yaml
# k8s/base/certificate.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: apex-api-tls
  namespace: apex
spec:
  secretName: apex-api-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - api.example.com
    - api-staging.example.com
```

### Certificate Rotation

#### Automated Rotation Script

```bash
#!/bin/bash
# scripts/rotate-certificates.sh

# Check certificate expiry
EXPIRY=$(kubectl get certificate apex-api-tls -n apex -o jsonpath='{.status.notAfter}')
EXPIRY_DATE=$(date -d "$EXPIRY" +%s)
CURRENT_DATE=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_DATE - $CURRENT_DATE) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
  echo "Certificate expires in $DAYS_UNTIL_EXPIRY days, renewing..."
  kubectl delete certificate apex-api-tls -n apex
  kubectl apply -f k8s/base/certificate.yaml
  kubectl wait --for=condition=Ready certificate apex-api-tls -n apex --timeout=5m
  echo "Certificate renewed"
fi
```

## Domain & DNS Setup

### CloudFlare Configuration

```yaml
# infra/dns/cloudflare-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudflare-dns
data:
  api.example.com: |
    type: A
    content: <load-balancer-ip>
    proxied: true
    ttl: 300
  api-staging.example.com: |
    type: A
    content: <staging-lb-ip>
    proxied: true
    ttl: 300
```

### Route53 Alternative

```hcl
# infra/terraform/modules/dns/route53.tf
resource "aws_route53_record" "api" {
  zone_id = var.route53_zone_id
  name    = "api.example.com"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
```

## Secrets Management

### HashiCorp Vault Integration

#### Vault Setup

```hcl
# infra/terraform/modules/vault/main.tf
resource "vault_mount" "apex" {
  path        = "apex"
  type        = "kv-v2"
  description = "APEX secrets"
}

resource "vault_kv_secret_v2" "apex_prod" {
  mount = vault_mount.apex.path
  name  = "prod"

  data_json = jsonencode({
    database_url     = var.database_url
    redis_url        = var.redis_url
    minio_access_key = var.minio_access_key
    minio_secret_key = var.minio_secret_key
  })
}
```

#### External Secrets Operator

```yaml
# k8s/base/external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: apex-secrets
  namespace: apex
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: apex-secrets
    creationPolicy: Owner
  data:
    - secretKey: APEX_DATABASE_URL
      remoteRef:
        key: apex/prod
        property: database_url
    - secretKey: APEX_REDIS_URL
      remoteRef:
        key: apex/prod
        property: redis_url
```

### AWS Secrets Manager Alternative

```yaml
# k8s/base/external-secret-aws.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: apex-secrets
  namespace: apex
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: apex-secrets
    creationPolicy: Owner
  data:
    - secretKey: APEX_DATABASE_URL
      remoteRef:
        key: apex/prod/database_url
```

## Environment Variables

### Production .env.example

```bash
# .env.prod.example
# Core Configuration
APEX_ENV=prod
APEX_SERVICE_NAME=api
APEX_APP_VERSION=0.1.0
APEX_DEPLOYMENT_ID=prod-us-east-1

# Database
APEX_DATABASE_URL=postgresql://apex:${DB_PASSWORD}@prod-db:5432/apex?sslmode=require

# Cache
APEX_REDIS_URL=redis://prod-redis:6379/0

# Storage
APEX_MINIO_URL=https://s3.example.com
APEX_MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
APEX_MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
APEX_MINIO_BUCKET=apex-prod

# Search
APEX_OPENSEARCH_URL=https://search.example.com

# CORS
APEX_CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com

# Rate Limiting
APEX_RATE_LIMIT_PER_MIN=100

# Tracing
APEX_OTEL_EXPORTER=otlp
APEX_OTEL_ENDPOINT=http://jaeger:4318

# Version Info
GIT_SHA=${GIT_SHA}
GIT_DIRTY=false
BUILD_ID=${BUILD_ID}
```

## Validation & Testing

### Terraform Validation

```bash
# Validate Terraform
cd infra/terraform/prod
terraform init
terraform validate
terraform fmt -check
terraform plan -out=prod.tfplan
```

### Helm Validation

```bash
# Lint Helm charts
helm lint k8s/charts/apex
helm template apex k8s/charts/apex -f k8s/charts/apex/values-prod.yaml | kubectl apply --dry-run=client -f -
```

### Link Validation

```bash
# Check documentation links
markdown-link-check docs/**/*.md
```

### Pre-Deployment Checklist

- [ ] Terraform plan reviewed and approved
- [ ] Helm chart linted and tested
- [ ] Secrets configured in Vault/AWS Secrets Manager
- [ ] SSL certificates issued and valid
- [ ] DNS records configured
- [ ] Monitoring and alerting enabled
- [ ] Backup procedures tested
- [ ] Rollback procedure documented
- [ ] Documentation updated
- [ ] Team notified of deployment

---

**Next Steps:**
- [**Operational Runbooks**](operational-runbooks.md) - Incident response procedures
- [**Security Hardening**](../security/security-hardening.md) - Security best practices
- [**Disaster Recovery**](disaster-recovery.md) - DR procedures

