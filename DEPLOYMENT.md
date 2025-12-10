# Ubuntu 24.04 LTS Server Deployment Guide

Complete guide for deploying ELAOMS (ElevenLabs Agents Open Memory System) on a fresh Ubuntu 24.04 LTS server.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Automated)](#quick-start-automated)
3. [Manual Setup](#manual-setup)
4. [SSL Configuration](#ssl-configuration)
5. [Service Management](#service-management)
6. [Troubleshooting](#troubleshooting)
7. [Production Environment Configuration](#production-environment-configuration)
8. [Production Checklist](#production-checklist)
9. [Architecture Overview](#architecture-overview)

---

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 24.04 LTS (Noble Numbat)
- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: Minimum 20GB
- **CPU**: 2+ cores recommended
- **Network**: Static IP or domain name for webhooks

### External Services Required

1. **ElevenLabs Account** - API keys from [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys)
2. **OpenMemory Service** - Running instance (local or remote)
3. **Domain Name** - Required for SSL/HTTPS (webhooks require HTTPS)

---

## Quick Start (Automated)

### One-Command Setup

```bash
# Clone the repository
git clone https://github.com/your-repo/elaoms.git
cd elaoms

# Run the automated setup script
sudo ./scripts/setup_ubuntu.sh --full
```

### What the Script Does

1. Updates system packages
2. Installs Python 3.12 and dependencies
3. Configures UFW firewall
4. Sets up Fail2ban for security
5. Creates Python virtual environment
6. Installs application dependencies
7. Configures systemd service
8. Sets up Nginx reverse proxy
9. Configures log rotation

### After Automated Setup

```bash
# 1. Configure environment variables
nano .env

# 2. Update Nginx with your domain
sudo nano /etc/nginx/sites-available/elaoms
# Replace YOUR_DOMAIN with your actual domain

# 3. Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx

# 4. Set up SSL
sudo certbot --nginx -d your-domain.com

# 5. Start the service
sudo systemctl start elaoms

# 6. Verify it's running
sudo systemctl status elaoms
curl http://localhost:8000/health
```

---

## Manual Setup

### Step 1: System Update

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 2: Install System Dependencies

```bash
# Essential tools
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    software-properties-common

# Python 3.12
sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip

# Web server and security
sudo apt-get install -y \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban
```

### Step 3: Configure Firewall

```bash
# Reset and configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

# Verify
sudo ufw status
```

### Step 4: Clone Repository

```bash
cd /home/ubuntu
git clone https://github.com/your-repo/elaoms.git
cd elaoms
```

### Step 5: Set Up Python Environment

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt
```

### Step 6: Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env
```

**Required Variables:**

```bash
# ElevenLabs API Keys
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_POST_CALL_KEY=your_hmac_secret
ELEVENLABS_CLIENT_DATA_KEY=your_client_data_key
ELEVENLABS_SEARCH_DATA_KEY=your_search_data_key

# OpenMemory Configuration
OPENMEMORY_KEY=your_openmemory_key
OPENMEMORY_PORT=8080

# Storage
PAYLOAD_STORAGE_PATH=./payloads
```

### Step 7: Create Required Directories

```bash
mkdir -p logs payloads data
chmod 755 logs payloads data
```

### Step 8: Test the Application

```bash
# Activate venv if not already
source venv/bin/activate

# Run in development mode
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Test health endpoint (in another terminal)
curl http://localhost:8000/health
```

### Step 9: Install Systemd Service

```bash
# Copy service file
sudo cp scripts/services/elaoms.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/elaoms.service

# Reload systemd and enable
sudo systemctl daemon-reload
sudo systemctl enable elaoms
sudo systemctl start elaoms

# Check status
sudo systemctl status elaoms
```

### Step 10: Configure Nginx

```bash
# Copy Nginx config
sudo cp scripts/services/nginx-elaoms.conf /etc/nginx/sites-available/elaoms

# Edit with your domain
sudo nano /etc/nginx/sites-available/elaoms
# Replace YOUR_DOMAIN with your actual domain

# Enable site
sudo ln -sf /etc/nginx/sites-available/elaoms /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## SSL Configuration

### Using Let's Encrypt (Recommended)

```bash
# Ensure DNS is pointing to your server, then run:
sudo certbot --nginx -d your-domain.com

# Certbot will:
# 1. Obtain a certificate
# 2. Update Nginx configuration
# 3. Set up auto-renewal

# Test auto-renewal
sudo certbot renew --dry-run
```

### Verify SSL

```bash
# Check certificate
curl -I https://your-domain.com/health

# Check expiry
sudo certbot certificates
```

---

## Service Management

### Systemd Commands

```bash
# Start service
sudo systemctl start elaoms

# Stop service
sudo systemctl stop elaoms

# Restart service
sudo systemctl restart elaoms

# Check status
sudo systemctl status elaoms

# Enable on boot
sudo systemctl enable elaoms

# Disable on boot
sudo systemctl disable elaoms
```

### Viewing Logs

```bash
# Systemd logs (live)
sudo journalctl -u elaoms -f

# Systemd logs (last 100 lines)
sudo journalctl -u elaoms -n 100

# Application logs
tail -f /home/ubuntu/elaoms/logs/uvicorn.log
tail -f /home/ubuntu/elaoms/logs/uvicorn-error.log

# Nginx logs
tail -f /var/log/nginx/elaoms_access.log
tail -f /var/log/nginx/elaoms_error.log
```

### Using run_local.sh (Development)

```bash
# Start server
./scripts/run_local.sh start

# Stop server
./scripts/run_local.sh stop

# Check status
./scripts/run_local.sh status

# View logs
./scripts/run_local.sh logs

# Debug mode
./scripts/run_local.sh debug

# With ngrok tunnel
./scripts/run_local.sh ngrok
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check for errors
sudo journalctl -u elaoms -n 50 --no-pager

# Common issues:
# 1. Missing .env file or variables
# 2. Wrong Python path in service file
# 3. Permission issues on directories
# 4. Port 8000 already in use

# Check if port is in use
sudo ss -tlnp | grep 8000

# Fix permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/elaoms
```

### Nginx Errors

```bash
# Test configuration
sudo nginx -t

# Check error log
sudo tail -50 /var/log/nginx/error.log

# Common issues:
# 1. Syntax error in config
# 2. Missing SSL certificates
# 3. Upstream server not running
```

### SSL Certificate Issues

```bash
# Renew manually
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Test SSL
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### Application Errors

```bash
# Check Python version
python3 --version  # Should be 3.12+

# Verify virtual environment
source venv/bin/activate
which python

# Test imports
python -c "import fastapi; print('FastAPI OK')"
python -c "import uvicorn; print('Uvicorn OK')"

# Run health check
curl http://localhost:8000/health

# Check OpenMemory connectivity
curl http://localhost:8080/health  # Adjust port as needed
```

### Firewall Issues

```bash
# Check UFW status
sudo ufw status verbose

# Check if ports are open
sudo ss -tlnp

# Temporarily disable (for testing)
sudo ufw disable

# Re-enable
sudo ufw enable
```

---

## Production Environment Configuration

This section details the complete production environment setup for ELAOMS with OpenMemory.

### Quick Production Setup

```bash
# 1. Copy the production environment template
cp .env.production .env

# 2. Generate secure API keys
# Use strong, random 32+ character strings for all keys
openssl rand -hex 32  # Generate random secrets

# 3. Edit with your actual values
nano .env

# 4. Set secure file permissions
chmod 600 .env
```

### Required API Keys

| Variable | Description | Where to Get It |
|----------|-------------|-----------------|
| `ELEVENLABS_API_KEY` | ElevenLabs SDK access | [ElevenLabs Settings](https://elevenlabs.io/app/settings/api-keys) |
| `ELEVENLABS_POST_CALL_KEY` | HMAC webhook secret | Agent webhook configuration in ElevenLabs |
| `ELEVENLABS_CLIENT_DATA_KEY` | Client-data API key | Generate with `openssl rand -hex 32` |
| `ELEVENLABS_SEARCH_DATA_KEY` | Search-data HMAC secret | Generate with `openssl rand -hex 32` |
| `OPENMEMORY_KEY` / `OM_API_KEY` | OpenMemory auth (must match) | Generate with `openssl rand -hex 32` |
| `OPENAI_API_KEY` | Embeddings API access | [OpenAI Platform](https://platform.openai.com/api-keys) |

### OpenMemory Production Settings

For production, the `.env.production` file includes optimized OpenMemory settings:

#### Database Backend (PostgreSQL)

```bash
# Create PostgreSQL database for OpenMemory
sudo -u postgres psql

CREATE DATABASE openmemory;
CREATE USER openmemory WITH ENCRYPTED PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE openmemory TO openmemory;
\q
```

#### Key Production Settings

| Category | Setting | Production Value | Purpose |
|----------|---------|-----------------|---------|
| **Security** | `OM_RATE_LIMIT_ENABLED` | `true` | Prevent abuse |
| **Security** | `OM_TELEMETRY` | `false` | Privacy |
| **Database** | `OM_METADATA_BACKEND` | `postgres` | Scalability |
| **Database** | `OM_PG_SSL` | `require` | Encrypted connections |
| **Embeddings** | `OM_EMBEDDINGS` | `openai` | Quality vectors |
| **Embeddings** | `OM_EMBED_MODE` | `batch` | Efficiency |
| **Performance** | `OM_TIER` | `hybrid` | Balanced performance |
| **Performance** | `OM_DECAY_THREADS` | `4` | Parallel processing |
| **Memory** | `OM_AUTO_REFLECT` | `true` | Context awareness |
| **Memory** | `OM_COMPRESSION_ENABLED` | `true` | Storage efficiency |

### Production Directory Structure

```bash
# Create production directories with proper permissions
sudo mkdir -p /var/lib/elaoms/payloads
sudo mkdir -p /var/lib/openmemory
sudo mkdir -p /var/log/elaoms

# Set ownership
sudo chown -R ubuntu:ubuntu /var/lib/elaoms
sudo chown -R ubuntu:ubuntu /var/lib/openmemory
sudo chown -R ubuntu:ubuntu /var/log/elaoms

# Set permissions
chmod 755 /var/lib/elaoms
chmod 755 /var/lib/openmemory
chmod 755 /var/log/elaoms
```

### Running OpenMemory Alongside ELAOMS

If running OpenMemory locally on the same server:

```bash
# Install OpenMemory
pip install openmemory

# Create systemd service for OpenMemory (example)
sudo tee /etc/systemd/system/openmemory.service > /dev/null <<EOF
[Unit]
Description=OpenMemory Cognitive Memory Engine
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/openmemory
EnvironmentFile=/home/ubuntu/elaoms/.env
ExecStart=/home/ubuntu/openmemory/venv/bin/openmemory serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable openmemory
sudo systemctl start openmemory
```

### Environment Files Summary

| File | Purpose | Git Tracked |
|------|---------|-------------|
| `.env.example` | Template with all variables documented | Yes |
| `.env.production` | Production-optimized template | Yes |
| `.env` | Active configuration (your secrets) | **No** |

### Security Best Practices

1. **API Key Management**
   - Use minimum 32-character random strings for all secrets
   - Rotate keys periodically (every 90 days recommended)
   - Never log or expose API keys in error messages

2. **File Permissions**
   ```bash
   chmod 600 .env              # Owner read/write only
   chmod 700 /var/lib/elaoms   # Owner full access only
   ```

3. **Network Security**
   - OpenMemory should only bind to localhost (`127.0.0.1:8080`)
   - Use HTTPS for all external webhook traffic
   - Enable rate limiting on both ELAOMS and OpenMemory

4. **Database Security**
   - Use strong PostgreSQL passwords
   - Enable SSL connections (`OM_PG_SSL=require`)
   - Restrict database user permissions

---

## Production Checklist

Before going live, verify:

### ELAOMS Application
- [ ] All environment variables configured in `.env` (copy from `.env.production`)
- [ ] File permissions set correctly (`chmod 600 .env`)
- [ ] Service starts automatically on reboot (`systemctl enable elaoms`)
- [ ] Health check endpoint accessible (`curl http://localhost:8000/health`)
- [ ] Webhook endpoints accessible via HTTPS

### OpenMemory Integration
- [ ] OpenMemory service running and healthy
- [ ] `OPENMEMORY_KEY` matches `OM_API_KEY` on OpenMemory server
- [ ] PostgreSQL database created and configured (production)
- [ ] OpenAI API key configured for embeddings
- [ ] Memory storage directories exist with proper permissions

### Security & Infrastructure
- [ ] Firewall rules properly configured (UFW enabled)
- [ ] SSL certificate installed and working (Let's Encrypt)
- [ ] Rate limiting enabled on both services
- [ ] Fail2ban running for security
- [ ] Log rotation configured
- [ ] Backup strategy in place for PostgreSQL and payload storage

### Connectivity Testing
```bash
# Test ELAOMS
curl -s http://localhost:8000/health | jq .

# Test OpenMemory
curl -s -H "Authorization: Bearer $OM_API_KEY" http://localhost:8080/health | jq .

# Test webhook accessibility (from external)
curl -s https://your-domain.com/webhooks/client-data -H "X-Api-Key: test" | jq .
```

---

## Architecture Overview

```
                    Internet
                        │
                        ▼
                   [Firewall]
                   UFW (80, 443)
                        │
                        ▼
                    [Nginx]
                 Reverse Proxy
                 SSL Termination
                 Rate Limiting
                        │
                        ▼
                    [Uvicorn]
                  ELAOMS FastAPI
                  localhost:8000
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
    [OpenMemory]               [ElevenLabs]
    Memory Storage             Voice AI Platform
```

---

## Support

For issues and feature requests, please open an issue on the repository.
