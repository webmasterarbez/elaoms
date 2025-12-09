#!/bin/bash
#===============================================================================
# Ubuntu 24.04 LTS Server Setup Script for ELAOMS
# ElevenLabs Agents Open Memory System
#===============================================================================
#
# Usage: sudo ./scripts/setup_ubuntu.sh [OPTIONS]
#
# Options:
#   --full          Full installation (system + app + services)
#   --app-only      Only install application dependencies
#   --services      Only configure systemd and nginx services
#   --help          Show this help message
#
# Prerequisites:
#   - Fresh Ubuntu 24.04 LTS server
#   - Root or sudo access
#   - Internet connection
#
#===============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.12"
APP_NAME="elaoms"
APP_USER="${SUDO_USER:-ubuntu}"
APP_DIR="/home/${APP_USER}/${APP_NAME}"
VENV_DIR="${APP_DIR}/venv"
LOG_DIR="${APP_DIR}/logs"
PAYLOAD_DIR="${APP_DIR}/payloads"

#-------------------------------------------------------------------------------
# Helper Functions
#-------------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

check_ubuntu_version() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" != "ubuntu" ]]; then
            log_warn "This script is designed for Ubuntu. Detected: $ID"
        fi
        if [[ "$VERSION_ID" != "24.04" ]]; then
            log_warn "This script is optimized for Ubuntu 24.04. Detected: $VERSION_ID"
        fi
    fi
}

#-------------------------------------------------------------------------------
# System Setup Functions
#-------------------------------------------------------------------------------

update_system() {
    log_info "Updating system packages..."
    apt-get update -y
    apt-get upgrade -y
    log_success "System updated"
}

install_system_dependencies() {
    log_info "Installing system dependencies..."

    # Essential build tools
    apt-get install -y \
        build-essential \
        git \
        curl \
        wget \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release

    # Python 3.12 and development headers
    apt-get install -y \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip

    # Set Python 3.12 as default python3
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

    # Networking tools
    apt-get install -y \
        nginx \
        certbot \
        python3-certbot-nginx \
        ufw

    # Process management
    apt-get install -y \
        supervisor \
        htop \
        iotop

    log_success "System dependencies installed"
}

configure_firewall() {
    log_info "Configuring UFW firewall..."

    # Reset to defaults
    ufw --force reset

    # Default policies
    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH (important: do this first!)
    ufw allow ssh
    ufw allow 22/tcp

    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Allow application port (for direct access if needed)
    ufw allow 8000/tcp

    # Enable firewall
    ufw --force enable

    log_success "Firewall configured"
    ufw status verbose
}

configure_fail2ban() {
    log_info "Installing and configuring Fail2ban..."

    apt-get install -y fail2ban

    # Create local configuration
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 24h
EOF

    systemctl enable fail2ban
    systemctl restart fail2ban

    log_success "Fail2ban configured"
}

#-------------------------------------------------------------------------------
# Application Setup Functions
#-------------------------------------------------------------------------------

setup_app_directories() {
    log_info "Setting up application directories..."

    # Create directories
    mkdir -p "${LOG_DIR}"
    mkdir -p "${PAYLOAD_DIR}"
    mkdir -p "${APP_DIR}/data"

    # Set ownership
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

    log_success "Application directories created"
}

setup_python_venv() {
    log_info "Setting up Python virtual environment..."

    # Create venv as the app user
    sudo -u "${APP_USER}" python${PYTHON_VERSION} -m venv "${VENV_DIR}"

    # Upgrade pip
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

    log_success "Virtual environment created at ${VENV_DIR}"
}

install_python_dependencies() {
    log_info "Installing Python dependencies..."

    if [[ -f "${APP_DIR}/requirements.txt" ]]; then
        sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"
        log_success "Production dependencies installed"
    else
        log_warn "requirements.txt not found at ${APP_DIR}/requirements.txt"
    fi

    # Install development dependencies if pyproject.toml exists
    if [[ -f "${APP_DIR}/pyproject.toml" ]]; then
        sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -e "${APP_DIR}[dev]" 2>/dev/null || true
        log_info "Development dependencies installed (if available)"
    fi
}

setup_environment_file() {
    log_info "Setting up environment file..."

    if [[ ! -f "${APP_DIR}/.env" ]]; then
        if [[ -f "${APP_DIR}/.env.example" ]]; then
            sudo -u "${APP_USER}" cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
            log_warn "Created .env from .env.example - Please configure it!"
            log_warn "Edit ${APP_DIR}/.env with your actual API keys and settings"
        else
            log_error ".env.example not found. Creating minimal .env template..."
            cat > "${APP_DIR}/.env" << 'EOF'
# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_POST_CALL_KEY=your_post_call_hmac_secret_here
ELEVENLABS_CLIENT_DATA_KEY=your_client_data_hmac_secret_here
ELEVENLABS_SEARCH_DATA_KEY=your_search_data_hmac_secret_here

# OpenMemory Configuration
OPENMEMORY_KEY=your_openmemory_api_key_here
OPENMEMORY_PORT=8080

# Storage Configuration
PAYLOAD_STORAGE_PATH=./payloads
EOF
            chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
            chmod 600 "${APP_DIR}/.env"
        fi
    else
        log_info ".env file already exists"
    fi
}

#-------------------------------------------------------------------------------
# Service Configuration Functions
#-------------------------------------------------------------------------------

setup_systemd_service() {
    log_info "Creating systemd service..."

    cat > /etc/systemd/system/${APP_NAME}.service << EOF
[Unit]
Description=ELAOMS - ElevenLabs Agents Open Memory System
Documentation=https://github.com/your-repo/elaoms
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=exec
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=${APP_DIR}/.env

ExecStart=${VENV_DIR}/bin/uvicorn app.main:app \\
    --host 127.0.0.1 \\
    --port 8000 \\
    --workers 4 \\
    --access-log \\
    --log-level info

ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
TimeoutStartSec=30
TimeoutStopSec=30

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${APP_DIR}/logs ${APP_DIR}/payloads ${APP_DIR}/data

# Logging
StandardOutput=append:${LOG_DIR}/uvicorn.log
StandardError=append:${LOG_DIR}/uvicorn-error.log
SyslogIdentifier=${APP_NAME}

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable ${APP_NAME}

    log_success "Systemd service created and enabled"
}

setup_nginx() {
    log_info "Configuring Nginx reverse proxy..."

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    # Create ELAOMS site configuration
    cat > /etc/nginx/sites-available/${APP_NAME} << 'EOF'
# ELAOMS Nginx Configuration
# Replace YOUR_DOMAIN with your actual domain

upstream elaoms_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=50r/s;

# HTTP -> HTTPS redirect (uncomment after SSL setup)
# server {
#     listen 80;
#     listen [::]:80;
#     server_name YOUR_DOMAIN;
#     return 301 https://$server_name$request_uri;
# }

server {
    listen 80;
    listen [::]:80;
    # listen 443 ssl http2;           # Uncomment after SSL setup
    # listen [::]:443 ssl http2;      # Uncomment after SSL setup

    server_name YOUR_DOMAIN localhost;

    # SSL Configuration (uncomment after running certbot)
    # ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
    # ssl_session_timeout 1d;
    # ssl_session_cache shared:SSL:50m;
    # ssl_session_tickets off;
    # ssl_protocols TLSv1.2 TLSv1.3;
    # ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    # ssl_prefer_server_ciphers off;
    # add_header Strict-Transport-Security "max-age=63072000" always;

    # Logging
    access_log /var/log/nginx/elaoms_access.log;
    error_log /var/log/nginx/elaoms_error.log;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Webhook endpoints (higher rate limit)
    location /webhook/ {
        limit_req zone=webhook_limit burst=100 nodelay;

        proxy_pass http://elaoms_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Webhook timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Don't buffer webhook requests
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint (no rate limit)
    location /health {
        proxy_pass http://elaoms_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Allow frequent health checks
        access_log off;
    }

    # API documentation
    location ~ ^/(docs|redoc|openapi.json)$ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://elaoms_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main API
    location / {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://elaoms_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/

    # Test configuration
    nginx -t

    # Reload nginx
    systemctl enable nginx
    systemctl reload nginx

    log_success "Nginx configured"
}

setup_logrotate() {
    log_info "Configuring log rotation..."

    cat > /etc/logrotate.d/${APP_NAME} << EOF
${LOG_DIR}/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ${APP_USER} ${APP_USER}
    sharedscripts
    postrotate
        systemctl reload ${APP_NAME} > /dev/null 2>&1 || true
    endscript
}
EOF

    log_success "Log rotation configured"
}

#-------------------------------------------------------------------------------
# SSL Setup
#-------------------------------------------------------------------------------

setup_ssl() {
    local domain="$1"

    if [[ -z "$domain" ]]; then
        log_warn "No domain provided. Skipping SSL setup."
        log_info "To set up SSL later, run: sudo certbot --nginx -d YOUR_DOMAIN"
        return
    fi

    log_info "Setting up SSL certificate for ${domain}..."

    # Update nginx config with domain
    sed -i "s/YOUR_DOMAIN/${domain}/g" /etc/nginx/sites-available/${APP_NAME}
    nginx -t && systemctl reload nginx

    # Get certificate
    certbot --nginx -d "${domain}" --non-interactive --agree-tos --email "admin@${domain}" --redirect

    # Set up auto-renewal
    systemctl enable certbot.timer
    systemctl start certbot.timer

    log_success "SSL certificate obtained for ${domain}"
}

#-------------------------------------------------------------------------------
# Main Functions
#-------------------------------------------------------------------------------

show_help() {
    cat << EOF
Ubuntu 24.04 LTS Server Setup Script for ELAOMS

Usage: sudo ./scripts/setup_ubuntu.sh [OPTIONS]

Options:
    --full              Full installation (system + app + services)
    --app-only          Only install application dependencies
    --services          Only configure systemd and nginx services
    --ssl DOMAIN        Set up SSL certificate for domain
    --help              Show this help message

Examples:
    # Full installation
    sudo ./scripts/setup_ubuntu.sh --full

    # Application dependencies only
    sudo ./scripts/setup_ubuntu.sh --app-only

    # Configure services
    sudo ./scripts/setup_ubuntu.sh --services

    # Set up SSL
    sudo ./scripts/setup_ubuntu.sh --ssl example.com

EOF
}

full_setup() {
    log_info "Starting full Ubuntu server setup for ELAOMS..."
    echo ""

    check_root
    check_ubuntu_version

    update_system
    install_system_dependencies
    configure_firewall
    configure_fail2ban
    setup_app_directories
    setup_python_venv
    install_python_dependencies
    setup_environment_file
    setup_systemd_service
    setup_nginx
    setup_logrotate

    echo ""
    log_success "=========================================="
    log_success "ELAOMS Server Setup Complete!"
    log_success "=========================================="
    echo ""
    log_info "Next steps:"
    echo "  1. Edit ${APP_DIR}/.env with your API keys"
    echo "  2. Configure your domain in /etc/nginx/sites-available/${APP_NAME}"
    echo "  3. Set up SSL: sudo certbot --nginx -d YOUR_DOMAIN"
    echo "  4. Start the service: sudo systemctl start ${APP_NAME}"
    echo "  5. Check status: sudo systemctl status ${APP_NAME}"
    echo ""
    log_info "Useful commands:"
    echo "  - View logs: sudo journalctl -u ${APP_NAME} -f"
    echo "  - Restart: sudo systemctl restart ${APP_NAME}"
    echo "  - Nginx logs: tail -f /var/log/nginx/elaoms_*.log"
    echo ""
}

app_only_setup() {
    log_info "Setting up application dependencies..."

    check_root
    setup_app_directories
    setup_python_venv
    install_python_dependencies
    setup_environment_file

    log_success "Application dependencies installed"
}

services_only_setup() {
    log_info "Configuring services..."

    check_root
    setup_systemd_service
    setup_nginx
    setup_logrotate

    log_success "Services configured"
}

#-------------------------------------------------------------------------------
# Main Entry Point
#-------------------------------------------------------------------------------

main() {
    case "${1:-}" in
        --full)
            full_setup
            ;;
        --app-only)
            app_only_setup
            ;;
        --services)
            services_only_setup
            ;;
        --ssl)
            check_root
            setup_ssl "${2:-}"
            ;;
        --help|-h)
            show_help
            ;;
        "")
            log_info "No option specified. Running full setup..."
            full_setup
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
