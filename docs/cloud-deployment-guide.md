# Cloud Deployment Guide for ELAOMS

This guide provides comprehensive recommendations for deploying the ElevenLabs Agents Open Memory System (ELAOMS) to cloud infrastructure.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Deployment Components](#deployment-components)
3. [Cloud Platform Recommendations](#cloud-platform-recommendations)
4. [Resource Requirements](#resource-requirements)
5. [Recommended Architecture by Scale](#recommended-architecture-by-scale)
6. [Infrastructure as Code Examples](#infrastructure-as-code-examples)
7. [Security Considerations](#security-considerations)
8. [Cost Estimates](#cost-estimates)
9. [Monitoring and Observability](#monitoring-and-observability)

---

## Architecture Overview

ELAOMS consists of two primary services that need to be deployed:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  ElevenLabs     │    │    Twilio       │    │   End Users     │         │
│  │  Agents API     │    │   Telephony     │    │   (Callers)     │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
└───────────┼──────────────────────┼──────────────────────┼──────────────────┘
            │                      │                      │
            ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLOUD INFRASTRUCTURE                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Load Balancer / CDN                           │   │
│  │                    (HTTPS Termination, SSL Certs)                    │   │
│  └────────────────────────────────┬─────────────────────────────────────┘   │
│                                   │                                          │
│                                   ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      ELAOMS FastAPI Service                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │ /client-data │  │ /search-data │  │ /post-call   │               │   │
│  │  │   webhook    │  │   webhook    │  │   webhook    │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │              Port 8000 | Python 3.12 | FastAPI/Uvicorn              │   │
│  └────────────────────────────────┬─────────────────────────────────────┘   │
│                                   │                                          │
│          ┌────────────────────────┴────────────────────────┐                │
│          │                                                  │                │
│          ▼                                                  ▼                │
│  ┌──────────────────────┐                    ┌──────────────────────┐       │
│  │   OpenMemory Server  │                    │   Persistent Storage │       │
│  │   Port 8080 (API)    │◀──────────────────▶│   (Payloads/Logs)    │       │
│  │   Port 3000 (UI)     │                    │                      │       │
│  └──────────────────────┘                    └──────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Components

### 1. ELAOMS FastAPI Application

**Purpose:** Handles webhook requests from ElevenLabs, processes call data, and manages memory operations.

| Attribute | Value |
|-----------|-------|
| Language | Python 3.12+ |
| Framework | FastAPI with Uvicorn |
| Port | 8000 |
| Health Check | `GET /health` |
| Startup Time | ~2-5 seconds |
| Memory Footprint | ~100-256 MB |
| CPU Requirements | Low (I/O bound) |

### 2. OpenMemory Server

**Purpose:** Cognitive memory engine for storing and retrieving caller profiles and conversation memories.

| Attribute | Value |
|-----------|-------|
| Components | Backend API (8080) + Dashboard UI (3000) |
| Database | SQLite (default) or PostgreSQL |
| Memory Footprint | ~512 MB - 2 GB |
| CPU Requirements | Moderate (vector operations) |
| Storage | Variable (depends on memory count) |

### 3. Persistent Storage

**Purpose:** Store conversation payloads (transcripts, audio files, failure logs).

| Attribute | Requirement |
|-----------|-------------|
| Type | Object storage or block storage |
| Estimated Size | ~100 KB - 500 KB per conversation |
| Access Pattern | Write-heavy, occasional reads |
| Retention | Configure based on compliance needs |

---

## Cloud Platform Recommendations

### Option 1: AWS (Recommended for Production)

**Best for:** Enterprise deployments, compliance requirements, maximum flexibility

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS VPC                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Application Load Balancer               │ │
│  │                (HTTPS, ACM Certificate)                    │ │
│  └───────────────────────────┬────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │                      ECS Fargate                          │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐        │  │
│  │  │  ELAOMS Service     │  │  OpenMemory Service │        │  │
│  │  │  (1-3 tasks)        │  │  (1-2 tasks)        │        │  │
│  │  └─────────────────────┘  └─────────────────────┘        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │   Amazon S3     │  │   Amazon EFS    │                │  │
│  │  │   (Payloads)    │  │   (OpenMemory DB)│                │  │
│  │  └─────────────────┘  └─────────────────┘                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │           AWS Secrets Manager (API Keys)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### AWS Services Required

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **ECS Fargate** | Container orchestration | 2 services (ELAOMS + OpenMemory) |
| **Application Load Balancer** | Traffic routing, HTTPS | 1 ALB with 2 target groups |
| **Amazon S3** | Payload storage | Standard tier, lifecycle policies |
| **Amazon EFS** | OpenMemory SQLite persistence | General purpose |
| **AWS Secrets Manager** | Secret storage | 8 secrets |
| **Amazon ECR** | Container registry | 2 repositories |
| **CloudWatch** | Logs and metrics | Log groups + alarms |
| **Route 53** | DNS management | Hosted zone + records |
| **ACM** | SSL certificates | 1 certificate |

### Option 2: Google Cloud Platform

**Best for:** Teams already using GCP, Kubernetes expertise

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Google Cloud                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Cloud Load Balancer                     │ │
│  │              (HTTPS, Managed Certificate)                  │ │
│  └───────────────────────────┬────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │                      Cloud Run                            │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐        │  │
│  │  │  ELAOMS Service     │  │  OpenMemory Service │        │  │
│  │  │  (auto-scaled)      │  │  (min 1 instance)   │        │  │
│  │  └─────────────────────┘  └─────────────────────┘        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │ Cloud Storage   │  │ Cloud SQL or    │                │  │
│  │  │ (Payloads)      │  │ Persistent Disk │                │  │
│  │  └─────────────────┘  └─────────────────┘                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Secret Manager (API Keys)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### GCP Services Required

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Cloud Run** | Serverless containers | 2 services |
| **Cloud Load Balancer** | Traffic routing | HTTPS with managed cert |
| **Cloud Storage** | Payload storage | Standard class |
| **Cloud SQL** | OpenMemory (if PostgreSQL) | db-f1-micro or higher |
| **Secret Manager** | Secret storage | 8 secrets |
| **Artifact Registry** | Container registry | 2 repositories |
| **Cloud Logging** | Centralized logging | Automatic |
| **Cloud DNS** | DNS management | Managed zone |

### Option 3: Railway / Render (Simplified PaaS)

**Best for:** Startups, MVPs, small teams, rapid deployment

#### Railway Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Railway                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Project Environment                      │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐        │ │
│  │  │  ELAOMS Service     │  │  OpenMemory Service │        │ │
│  │  │  (from GitHub)      │  │  (from Docker)      │        │ │
│  │  │  Auto HTTPS ✓       │  │  Auto HTTPS ✓       │        │ │
│  │  └─────────────────────┘  └─────────────────────┘        │ │
│  │                                                            │ │
│  │  ┌─────────────────────┐                                  │ │
│  │  │  Persistent Volume  │ ← OpenMemory SQLite + Payloads   │ │
│  │  │  (100 GB)           │                                  │ │
│  │  └─────────────────────┘                                  │ │
│  │                                                            │ │
│  │  Environment Variables: Managed via Railway Dashboard      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Option 4: DigitalOcean

**Best for:** Cost-conscious deployments, simpler management

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       DigitalOcean                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    App Platform                            │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐        │ │
│  │  │  ELAOMS Service     │  │  OpenMemory Service │        │ │
│  │  │  (Web Service)      │  │  (Worker Service)   │        │ │
│  │  └─────────────────────┘  └─────────────────────┘        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐  │
│  │  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │    Spaces       │  │   Managed DB    │                │  │
│  │  │  (Payloads)     │  │  (PostgreSQL)   │                │  │
│  │  └─────────────────┘  └─────────────────┘                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Resource Requirements

### Minimum (Development/Testing)

| Component | CPU | Memory | Storage | Monthly Cost Est. |
|-----------|-----|--------|---------|-------------------|
| ELAOMS | 0.25 vCPU | 256 MB | - | $5-10 |
| OpenMemory | 0.5 vCPU | 512 MB | 10 GB | $10-20 |
| Storage | - | - | 10 GB | $1-5 |
| **Total** | **0.75 vCPU** | **768 MB** | **20 GB** | **$16-35/mo** |

### Small Production (< 1000 calls/day)

| Component | CPU | Memory | Storage | Monthly Cost Est. |
|-----------|-----|--------|---------|-------------------|
| ELAOMS | 0.5 vCPU | 512 MB | - | $15-25 |
| OpenMemory | 1 vCPU | 1 GB | 50 GB | $30-50 |
| Storage | - | - | 50 GB | $5-10 |
| Load Balancer | - | - | - | $15-20 |
| **Total** | **1.5 vCPU** | **1.5 GB** | **100 GB** | **$65-105/mo** |

### Medium Production (1000-10000 calls/day)

| Component | CPU | Memory | Storage | Instances | Monthly Cost Est. |
|-----------|-----|--------|---------|-----------|-------------------|
| ELAOMS | 1 vCPU | 1 GB | - | 2-3 | $50-100 |
| OpenMemory | 2 vCPU | 2 GB | 100 GB | 2 | $80-150 |
| Storage | - | - | 200 GB | - | $20-40 |
| Load Balancer | - | - | - | 1 | $20-30 |
| Database (if PostgreSQL) | 2 vCPU | 4 GB | 100 GB | 1 | $50-100 |
| **Total** | **8 vCPU** | **10 GB** | **400 GB** | - | **$220-420/mo** |

### Large Production (> 10000 calls/day)

| Component | CPU | Memory | Storage | Instances | Monthly Cost Est. |
|-----------|-----|--------|---------|-----------|-------------------|
| ELAOMS | 2 vCPU | 2 GB | - | 3-5 | $150-300 |
| OpenMemory | 4 vCPU | 8 GB | 500 GB | 2-3 | $200-400 |
| Storage | - | - | 1 TB | - | $50-100 |
| Load Balancer | - | - | - | 1 | $30-50 |
| Database (PostgreSQL) | 4 vCPU | 16 GB | 500 GB | 1 (HA) | $200-400 |
| CDN | - | - | - | - | $50-100 |
| **Total** | **20+ vCPU** | **40+ GB** | **2+ TB** | - | **$680-1350/mo** |

---

## Recommended Architecture by Scale

### Startup / MVP Deployment

**Platform:** Railway or Render

```yaml
# railway.toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 10
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 5

[[services]]
name = "elaoms"
```

**Pros:**
- 5-minute deployment
- Automatic HTTPS
- Git-based deployments
- Built-in environment variable management

**Cons:**
- Limited customization
- Shared infrastructure
- Less control over networking

### Small Business Deployment

**Platform:** AWS ECS Fargate or GCP Cloud Run

**Key Decisions:**
1. Use managed services where possible
2. Single-region deployment
3. Auto-scaling based on request count
4. S3/GCS for payload storage

### Enterprise Deployment

**Platform:** AWS ECS/EKS or GKE

**Key Decisions:**
1. Multi-AZ/Multi-region for high availability
2. Private subnets with NAT gateway
3. Dedicated database instances
4. WAF for additional security
5. VPC peering if needed
6. Comprehensive monitoring and alerting

---

## Infrastructure as Code Examples

### Docker Compose (Local/Simple Deployment)

```yaml
# docker-compose.yml
version: '3.8'

services:
  elaoms:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - ELEVENLABS_POST_CALL_KEY=${ELEVENLABS_POST_CALL_KEY}
      - ELEVENLABS_CLIENT_DATA_KEY=${ELEVENLABS_CLIENT_DATA_KEY}
      - ELEVENLABS_SEARCH_DATA_KEY=${ELEVENLABS_SEARCH_DATA_KEY}
      - OPENMEMORY_KEY=${OPENMEMORY_KEY}
      - OPENMEMORY_PORT=http://openmemory:8080
      - OPENMEMORY_DB_PATH=/data/openmemory.db
      - PAYLOAD_STORAGE_PATH=/data/payloads
    volumes:
      - payload-data:/data/payloads
    depends_on:
      - openmemory
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  openmemory:
    image: caviraoss/openmemory:latest
    ports:
      - "8080:8080"
      - "3000:3000"
    environment:
      - OPENMEMORY_API_KEY=${OPENMEMORY_KEY}
    volumes:
      - openmemory-data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - elaoms
    restart: unless-stopped

volumes:
  payload-data:
  openmemory-data:
```

### Production Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy application
COPY app/ ./app/

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### Terraform (AWS ECS Fargate)

```hcl
# terraform/main.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "production"
}

variable "app_name" {
  default = "elaoms"
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.app_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    Environment = var.environment
    Application = var.app_name
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Definition - ELAOMS
resource "aws_ecs_task_definition" "elaoms" {
  family                   = "${var.app_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "elaoms"
      image = "${aws_ecr_repository.elaoms.repository_url}:latest"

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "OPENMEMORY_PORT"
          value = "http://openmemory.${var.app_name}.local:8080"
        },
        {
          name  = "PAYLOAD_STORAGE_PATH"
          value = "/data/payloads"
        }
      ]

      secrets = [
        {
          name      = "ELEVENLABS_API_KEY"
          valueFrom = aws_secretsmanager_secret.elevenlabs_api_key.arn
        },
        {
          name      = "ELEVENLABS_POST_CALL_KEY"
          valueFrom = aws_secretsmanager_secret.elevenlabs_post_call_key.arn
        },
        {
          name      = "OPENMEMORY_KEY"
          valueFrom = aws_secretsmanager_secret.openmemory_key.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.elaoms.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 10
      }
    }
  ])
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = true
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.elaoms.arn
  }
}

# S3 Bucket for Payloads
resource "aws_s3_bucket" "payloads" {
  bucket = "${var.app_name}-payloads-${var.environment}"

  tags = {
    Environment = var.environment
    Application = var.app_name
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "payloads" {
  bucket = aws_s3_bucket.payloads.id

  rule {
    id     = "archive-old-payloads"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.app_name}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.elaoms.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# Auto Scaling
resource "aws_appautoscaling_target" "elaoms" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.elaoms.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "elaoms_cpu" {
  name               = "${var.app_name}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.elaoms.resource_id
  scalable_dimension = aws_appautoscaling_target.elaoms.scalable_dimension
  service_namespace  = aws_appautoscaling_target.elaoms.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
```

---

## Security Considerations

### Network Security

| Requirement | Implementation |
|-------------|----------------|
| HTTPS Only | Terminate TLS at load balancer, redirect HTTP to HTTPS |
| Private Subnets | Deploy application containers in private subnets |
| Security Groups | Restrict ingress to ALB, egress to required services |
| VPC Endpoints | Use for AWS services to avoid public internet |

### Secret Management

| Secret | Storage Recommendation |
|--------|------------------------|
| `ELEVENLABS_API_KEY` | AWS Secrets Manager / GCP Secret Manager |
| `ELEVENLABS_POST_CALL_KEY` | AWS Secrets Manager / GCP Secret Manager |
| `OPENMEMORY_KEY` | AWS Secrets Manager / GCP Secret Manager |
| Other HMAC Keys | AWS Secrets Manager / GCP Secret Manager |

### Application Security

- [ ] Enable HMAC validation for all webhooks (currently only post-call)
- [ ] Implement rate limiting at ALB/API Gateway level
- [ ] Enable WAF rules for common attack patterns
- [ ] Regular dependency vulnerability scanning
- [ ] Container image scanning in ECR/GCR

### Compliance Considerations

| Requirement | Implementation |
|-------------|----------------|
| Data Encryption at Rest | Enable S3/EFS encryption, RDS encryption |
| Data Encryption in Transit | TLS 1.3, HTTPS only |
| Access Logging | ALB access logs, CloudTrail, CloudWatch Logs |
| Data Retention | Configure lifecycle policies based on compliance |
| PII Handling | Phone numbers are PII - ensure proper handling |

---

## Cost Estimates

### AWS Cost Breakdown (Medium Production)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| ECS Fargate (ELAOMS) | 2 tasks × 0.5 vCPU × 1 GB | ~$30 |
| ECS Fargate (OpenMemory) | 1 task × 1 vCPU × 2 GB | ~$35 |
| Application Load Balancer | 1 ALB + data processing | ~$25 |
| S3 (Payloads) | 50 GB standard | ~$1.15 |
| EFS (OpenMemory DB) | 20 GB | ~$6 |
| Secrets Manager | 8 secrets | ~$3.20 |
| CloudWatch Logs | 10 GB/month | ~$5 |
| NAT Gateway | 1 gateway + data transfer | ~$35 |
| **Total** | | **~$140/month** |

### GCP Cost Breakdown (Medium Production)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud Run (ELAOMS) | 2 instances min | ~$25 |
| Cloud Run (OpenMemory) | 1 instance min | ~$30 |
| Cloud Load Balancer | Global HTTPS LB | ~$20 |
| Cloud Storage | 50 GB | ~$1 |
| Cloud SQL (PostgreSQL) | db-f1-micro | ~$10 |
| Secret Manager | 8 secrets | ~$0.50 |
| Cloud Logging | 10 GB | ~$5 |
| **Total** | | **~$90/month** |

### Railway Cost Breakdown (Small Production)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| ELAOMS Service | 512 MB / 0.5 vCPU | ~$5 |
| OpenMemory Service | 1 GB / 1 vCPU | ~$10 |
| Persistent Volume | 10 GB | ~$1 |
| **Total** | | **~$16/month** |

---

## Monitoring and Observability

### Required Metrics

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Request Latency (p99) | ALB/Cloud Run | > 500ms |
| Error Rate (5xx) | ALB/Cloud Run | > 1% |
| CPU Utilization | ECS/Cloud Run | > 80% |
| Memory Utilization | ECS/Cloud Run | > 85% |
| Webhook Processing Time | Application | > 2s |
| OpenMemory Query Latency | Application | > 200ms |

### Logging Strategy

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Application    │────▶│  Log Aggregator │────▶│  Log Storage    │
│  (JSON Logs)    │     │  (CloudWatch/   │     │  (S3/GCS for    │
│                 │     │   Cloud Logging)│     │   long-term)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Alerting       │
                        │  (PagerDuty/    │
                        │   SNS/Slack)    │
                        └─────────────────┘
```

### Recommended Log Fields

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "elaoms",
  "endpoint": "/webhook/client-data",
  "caller_id": "+1612978XXXX",
  "conversation_id": "conv_xxx",
  "duration_ms": 45,
  "status_code": 200,
  "trace_id": "abc123"
}
```

### Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Basic health | `{"status": "healthy"}` |
| `/health/ready` | Readiness (add) | Include dependency checks |
| `/health/live` | Liveness (add) | Simple alive check |

---

## Deployment Checklist

### Pre-Deployment

- [ ] All environment variables configured
- [ ] SSL certificate provisioned
- [ ] DNS records created
- [ ] Security groups/firewall rules configured
- [ ] Secrets stored in secrets manager
- [ ] Container images built and pushed
- [ ] Database/storage provisioned

### Post-Deployment

- [ ] Health check passing
- [ ] Webhook endpoints accessible via HTTPS
- [ ] ElevenLabs Agent configured with webhook URLs
- [ ] Test call successfully processed
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Runbook documented

### Webhook URLs to Configure in ElevenLabs

```
Client-Data Webhook: https://your-domain.com/webhook/client-data
Search-Data Webhook: https://your-domain.com/webhook/search-data
Post-Call Webhook:   https://your-domain.com/webhook/post-call
```

---

## Summary Recommendations

| Scale | Platform | Estimated Cost | Deployment Complexity |
|-------|----------|----------------|----------------------|
| **MVP/Startup** | Railway/Render | $16-35/mo | Low (5 min) |
| **Small Business** | GCP Cloud Run | $90-150/mo | Medium (1-2 hours) |
| **Medium Business** | AWS ECS Fargate | $140-250/mo | Medium-High (2-4 hours) |
| **Enterprise** | AWS EKS/GKE | $500-1500/mo | High (1-2 days) |

**Primary Recommendation:** Start with **Railway or GCP Cloud Run** for rapid deployment, then migrate to **AWS ECS Fargate** as scale and compliance requirements increase.
