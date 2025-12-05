#!/bin/bash
# =============================================================================
# ELAOMS + OpenMemory Ubuntu Server Installation Script
# =============================================================================
# This script installs and configures:
# - ELAOMS (ElevenLabs Agents OpenMemory System)
# - OpenMemory (Cognitive Memory System)
# - OpenMemory Dashboard
# - Nginx with SSL (Let's Encrypt)
# - Password protection for sensitive endpoints
#
# Requirements:
# - Ubuntu 24.04 LTS
# - Root/sudo access
# - Domain pointed to server IP
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Configuration Variables (Edit these or pass as environment variables)
# =============================================================================
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

# API Keys (will prompt if not set)
ELEVENLABS_API_KEY="${ELEVENLABS_API_KEY:-}"
ELEVENLABS_POST_CALL_KEY="${ELEVENLABS_POST_CALL_KEY:-}"
ELEVENLABS_CLIENT_DATA_KEY="${ELEVENLABS_CLIENT_DATA_KEY:-}"
ELEVENLABS_SEARCH_DATA_KEY="${ELEVENLABS_SEARCH_DATA_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# Installation paths
ELAOMS_PATH="/opt/elaoms"
OPENMEMORY_PATH="/opt/openmemory"

# =============================================================================
# Helper Functions
# =============================================================================
print_header() {
    echo -e "\n${BLUE}=============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=============================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

prompt_if_empty() {
    local var_name=$1
    local prompt_text=$2
    local is_secret=${3:-false}

    eval "local current_value=\$$var_name"

    if [ -z "$current_value" ]; then
        if [ "$is_secret" = true ]; then
            read -sp "$prompt_text: " value
            echo
        else
            read -p "$prompt_text: " value
        fi
        eval "$var_name='$value'"
    fi
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run as root or with sudo"
        exit 1
    fi
}

# =============================================================================
# Step 1: Gather Configuration
# =============================================================================
gather_config() {
    print_header "Configuration Setup"

    prompt_if_empty DOMAIN "Enter your domain (e.g., elaoms.example.com)"
    prompt_if_empty EMAIL "Enter your email (for SSL certificate)"
    prompt_if_empty ADMIN_PASSWORD "Enter admin password for dashboard" true

    echo ""
    print_warning "API Keys Configuration"
    echo "You can skip these now and configure them later in the .env files"
    echo ""

    read -p "Configure API keys now? (y/n): " configure_keys
    if [ "$configure_keys" = "y" ] || [ "$configure_keys" = "Y" ]; then
        prompt_if_empty ELEVENLABS_API_KEY "ElevenLabs API Key" true
        prompt_if_empty ELEVENLABS_POST_CALL_KEY "ElevenLabs Post-Call HMAC Key" true
        prompt_if_empty ELEVENLABS_CLIENT_DATA_KEY "ElevenLabs Client-Data HMAC Key" true
        prompt_if_empty ELEVENLABS_SEARCH_DATA_KEY "ElevenLabs Search-Data HMAC Key" true
        prompt_if_empty OPENAI_API_KEY "OpenAI API Key (for embeddings)" true
    fi

    # Generate OpenMemory API key
    OPENMEMORY_API_KEY=$(openssl rand -hex 32)

    print_success "Configuration gathered"
}

# =============================================================================
# Step 2: System Update and Basic Tools
# =============================================================================
install_base() {
    print_header "Step 1: System Update and Basic Tools"

    apt update && apt upgrade -y
    apt install -y \
        curl \
        wget \
        git \
        ufw \
        software-properties-common \
        build-essential \
        apache2-utils

    print_success "Base packages installed"
}

# =============================================================================
# Step 3: Configure Firewall
# =============================================================================
configure_firewall() {
    print_header "Step 2: Configuring Firewall"

    ufw allow OpenSSH
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable

    print_success "Firewall configured"
}

# =============================================================================
# Step 4: Install Python 3.12
# =============================================================================
install_python() {
    print_header "Step 3: Installing Python 3.12"

    apt install -y python3-pip python3-venv python3-dev

    # Create symlink if not exists
    if [ ! -f /usr/bin/python ]; then
        update-alternatives --install /usr/bin/python python /usr/bin/python3 1
    fi

    print_success "Python $(python3 --version) installed"
}

# =============================================================================
# Step 5: Install Node.js 20 LTS
# =============================================================================
install_nodejs() {
    print_header "Step 4: Installing Node.js 20 LTS"

    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs

    print_success "Node.js $(node --version) installed"
}

# =============================================================================
# Step 6: Install Nginx
# =============================================================================
install_nginx() {
    print_header "Step 5: Installing Nginx"

    apt install -y nginx
    systemctl start nginx
    systemctl enable nginx

    print_success "Nginx installed and running"
}

# =============================================================================
# Step 7: Install Certbot
# =============================================================================
install_certbot() {
    print_header "Step 6: Installing Certbot"

    apt install -y certbot python3-certbot-nginx

    print_success "Certbot installed"
}

# =============================================================================
# Step 8: Clone and Setup ELAOMS
# =============================================================================
setup_elaoms() {
    print_header "Step 7: Setting up ELAOMS"

    # Create directory
    mkdir -p $ELAOMS_PATH

    # Clone repository
    if [ -d "$ELAOMS_PATH/.git" ]; then
        print_warning "ELAOMS already cloned, pulling latest"
        cd $ELAOMS_PATH && git pull
    else
        git clone https://github.com/webmasterarbez/elevenlabs_agents_open_memory_system.git $ELAOMS_PATH
    fi

    cd $ELAOMS_PATH

    # Remove old venv if exists (might be from different system)
    rm -rf venv

    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies
    pip install --upgrade pip
    pip install -r requirements.txt

    # Create data directories
    mkdir -p data payloads

    # Create .env file
    cat > $ELAOMS_PATH/.env << EOF
# ElevenLabs Configuration
ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:-your_elevenlabs_api_key}
ELEVENLABS_POST_CALL_KEY=${ELEVENLABS_POST_CALL_KEY:-your_post_call_hmac_key}
ELEVENLABS_CLIENT_DATA_KEY=${ELEVENLABS_CLIENT_DATA_KEY:-your_client_data_hmac_key}
ELEVENLABS_SEARCH_DATA_KEY=${ELEVENLABS_SEARCH_DATA_KEY:-your_search_data_hmac_key}

# OpenMemory Configuration
OPENMEMORY_KEY=${OPENMEMORY_API_KEY}
OPENMEMORY_PORT=8080
OPENMEMORY_DB_PATH=${OPENMEMORY_PATH}/data/openmemory.db

# Storage Configuration
PAYLOAD_STORAGE_PATH=${ELAOMS_PATH}/payloads
EOF

    deactivate

    print_success "ELAOMS installed at $ELAOMS_PATH"
}

# =============================================================================
# Step 9: Clone and Setup OpenMemory
# =============================================================================
setup_openmemory() {
    print_header "Step 8: Setting up OpenMemory"

    # Create directory
    mkdir -p $OPENMEMORY_PATH

    # Clone repository
    if [ -d "$OPENMEMORY_PATH/.git" ]; then
        print_warning "OpenMemory already cloned, pulling latest"
        cd $OPENMEMORY_PATH && git pull
    else
        git clone https://github.com/CaviraOSS/OpenMemory.git $OPENMEMORY_PATH
    fi

    cd $OPENMEMORY_PATH

    # Create data directory
    mkdir -p data

    # Install backend dependencies
    cd backend
    npm install
    npm run build

    # Create .env file for backend
    cat > $OPENMEMORY_PATH/.env << EOF
# =============================================================================
# Server Settings
# =============================================================================
OM_PORT=8080
OM_API_KEY=${OPENMEMORY_API_KEY}
OM_MODE=standard
OM_TELEMETRY=false

# =============================================================================
# Database - SQLite
# =============================================================================
OM_METADATA_BACKEND=sqlite
OM_DB_PATH=${OPENMEMORY_PATH}/data/openmemory.db
OM_VECTOR_BACKEND=sqlite
OM_VECTOR_TABLE=vectors

# =============================================================================
# Performance - HIGH PERFORMANCE settings
# =============================================================================
OM_TIER=deep
OM_MIN_SCORE=0.5

# =============================================================================
# DECAY - DISABLED (memories persist forever)
# =============================================================================
OM_DECAY_INTERVAL_MINUTES=0
OM_DECAY_THREADS=0
OM_DECAY_COLD_THRESHOLD=0
OM_DECAY_REINFORCE_ON_QUERY=false

# =============================================================================
# Embeddings
# =============================================================================
OM_EMBEDDINGS=openai
OM_EMBED_MODE=simple
OPENAI_API_KEY=${OPENAI_API_KEY:-your_openai_api_key}

# =============================================================================
# Storage Optimization
# =============================================================================
OM_REGENERATION_ENABLED=false
OM_USE_SUMMARY_ONLY=false
OM_COMPRESSION_ENABLED=false

# =============================================================================
# Auto-Reflection - DISABLED
# =============================================================================
OM_AUTO_REFLECT=false

# =============================================================================
# Rate Limiting - Disabled for internal use
# =============================================================================
OM_RATE_LIMIT_ENABLED=false
EOF

    # Copy .env to backend directory
    cp $OPENMEMORY_PATH/.env $OPENMEMORY_PATH/backend/.env

    print_success "OpenMemory backend installed at $OPENMEMORY_PATH"
}

# =============================================================================
# Step 10: Setup OpenMemory Dashboard
# =============================================================================
setup_dashboard() {
    print_header "Step 9: Setting up OpenMemory Dashboard"

    cd $OPENMEMORY_PATH/dashboard

    # Install dependencies
    npm install

    # Create .env.local
    cat > $OPENMEMORY_PATH/dashboard/.env.local << EOF
NEXT_PUBLIC_API_URL=http://127.0.0.1:8080
NEXT_PUBLIC_API_KEY=${OPENMEMORY_API_KEY}
EOF

    # Build dashboard
    npm run build

    print_success "OpenMemory Dashboard built"
}

# =============================================================================
# Step 11: Create Systemd Services
# =============================================================================
create_services() {
    print_header "Step 10: Creating Systemd Services"

    # Get the user who ran sudo
    INSTALL_USER=${SUDO_USER:-ubuntu}

    # ELAOMS Service
    cat > /etc/systemd/system/elaoms.service << EOF
[Unit]
Description=ELAOMS - ElevenLabs Agents OpenMemory System
After=network.target

[Service]
Type=simple
User=${INSTALL_USER}
Group=${INSTALL_USER}
WorkingDirectory=${ELAOMS_PATH}
Environment="PATH=${ELAOMS_PATH}/venv/bin:/usr/bin"
EnvironmentFile=${ELAOMS_PATH}/.env
ExecStart=${ELAOMS_PATH}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # OpenMemory Service
    cat > /etc/systemd/system/openmemory.service << EOF
[Unit]
Description=OpenMemory - Cognitive Memory System
After=network.target

[Service]
Type=simple
User=${INSTALL_USER}
Group=${INSTALL_USER}
WorkingDirectory=${OPENMEMORY_PATH}/backend
Environment="NODE_ENV=production"
EnvironmentFile=${OPENMEMORY_PATH}/.env
ExecStart=/usr/bin/node ${OPENMEMORY_PATH}/backend/dist/server.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # OpenMemory Dashboard Service
    cat > /etc/systemd/system/openmemory-dashboard.service << EOF
[Unit]
Description=OpenMemory Dashboard
After=network.target openmemory.service

[Service]
Type=simple
User=${INSTALL_USER}
Group=${INSTALL_USER}
WorkingDirectory=${OPENMEMORY_PATH}/dashboard
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload

    # Enable services
    systemctl enable elaoms
    systemctl enable openmemory
    systemctl enable openmemory-dashboard

    print_success "Systemd services created"
}

# =============================================================================
# Step 12: Configure Nginx
# =============================================================================
configure_nginx() {
    print_header "Step 11: Configuring Nginx"

    # Create htpasswd file
    htpasswd -bc /etc/nginx/.htpasswd "$ADMIN_USER" "$ADMIN_PASSWORD"

    # Create Nginx config
    cat > /etc/nginx/sites-available/$DOMAIN << 'NGINX_CONFIG'
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name DOMAIN_PLACEHOLDER;

    ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # =====================================================
    # PUBLIC: Webhooks (no auth - ElevenLabs needs access)
    # =====================================================
    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # =====================================================
    # PROTECTED: Everything else (password required)
    # =====================================================

    # Docs (Swagger UI)
    location /docs {
        auth_basic "ELAOMS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ReDoc
    location /redoc {
        auth_basic "ELAOMS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # OpenAPI JSON
    location /openapi.json {
        auth_basic "ELAOMS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        auth_basic "ELAOMS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Root endpoint
    location = / {
        auth_basic "ELAOMS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # OpenMemory Dashboard (password protected)
    location /openmemory/dashboard {
        auth_basic "OpenMemory Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Dashboard static files
    location /_next {
        auth_basic "OpenMemory Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Block everything else
    location / {
        return 404;
    }
}
NGINX_CONFIG

    # Replace domain placeholder
    sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /etc/nginx/sites-available/$DOMAIN

    # Enable site
    ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    print_success "Nginx configured"
}

# =============================================================================
# Step 13: Get SSL Certificate
# =============================================================================
get_ssl_certificate() {
    print_header "Step 12: Obtaining SSL Certificate"

    # First, create a temporary config for initial SSL
    cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    # Test and reload nginx
    nginx -t
    systemctl reload nginx

    # Get certificate
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL

    print_success "SSL certificate obtained"

    # Now apply full config with SSL
    configure_nginx

    # Test and reload
    nginx -t
    systemctl reload nginx

    print_success "Full Nginx config applied with SSL"
}

# =============================================================================
# Step 14: Start Services
# =============================================================================
start_services() {
    print_header "Step 13: Starting Services"

    systemctl start openmemory
    sleep 2
    systemctl start elaoms
    sleep 2
    systemctl start openmemory-dashboard

    print_success "All services started"
}

# =============================================================================
# Step 15: Verify Installation
# =============================================================================
verify_installation() {
    print_header "Step 14: Verifying Installation"

    echo "Checking services..."

    # Check ELAOMS
    if systemctl is-active --quiet elaoms; then
        print_success "ELAOMS is running"
    else
        print_error "ELAOMS is not running"
        systemctl status elaoms --no-pager
    fi

    # Check OpenMemory
    if systemctl is-active --quiet openmemory; then
        print_success "OpenMemory is running"
    else
        print_error "OpenMemory is not running"
        systemctl status openmemory --no-pager
    fi

    # Check Dashboard
    if systemctl is-active --quiet openmemory-dashboard; then
        print_success "OpenMemory Dashboard is running"
    else
        print_error "OpenMemory Dashboard is not running"
        systemctl status openmemory-dashboard --no-pager
    fi

    # Check Nginx
    if systemctl is-active --quiet nginx; then
        print_success "Nginx is running"
    else
        print_error "Nginx is not running"
    fi

    echo ""
    echo "Testing endpoints..."

    # Test local endpoints
    if curl -s http://127.0.0.1:8000/health | grep -q "healthy"; then
        print_success "ELAOMS health check passed"
    else
        print_warning "ELAOMS health check failed"
    fi

    if curl -s http://127.0.0.1:8080/health | grep -q "ok"; then
        print_success "OpenMemory health check passed"
    else
        print_warning "OpenMemory health check failed"
    fi
}

# =============================================================================
# Step 16: Print Summary
# =============================================================================
print_summary() {
    print_header "Installation Complete!"

    echo -e "${GREEN}Your server is now configured with:${NC}"
    echo ""
    echo "  ELAOMS API:        https://$DOMAIN"
    echo "  API Docs:          https://$DOMAIN/docs (protected)"
    echo "  Health Check:      https://$DOMAIN/health (protected)"
    echo "  Webhooks:          https://$DOMAIN/webhook/* (public)"
    echo "  Dashboard:         https://$DOMAIN/openmemory/dashboard (protected)"
    echo ""
    echo -e "${YELLOW}Login Credentials:${NC}"
    echo "  Username: $ADMIN_USER"
    echo "  Password: (the password you entered)"
    echo ""
    echo -e "${YELLOW}OpenMemory API Key:${NC}"
    echo "  $OPENMEMORY_API_KEY"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  sudo systemctl status elaoms openmemory openmemory-dashboard"
    echo "  sudo systemctl restart elaoms openmemory openmemory-dashboard"
    echo "  sudo journalctl -u elaoms -f"
    echo "  sudo journalctl -u openmemory -f"
    echo ""
    echo -e "${YELLOW}Configuration Files:${NC}"
    echo "  ELAOMS:      $ELAOMS_PATH/.env"
    echo "  OpenMemory:  $OPENMEMORY_PATH/.env"
    echo "  Dashboard:   $OPENMEMORY_PATH/dashboard/.env.local"
    echo "  Nginx:       /etc/nginx/sites-available/$DOMAIN"
    echo ""
    echo -e "${GREEN}Setup complete! Configure your ElevenLabs Agent webhooks to:${NC}"
    echo "  POST https://$DOMAIN/webhook/client-data"
    echo "  POST https://$DOMAIN/webhook/search-data"
    echo "  POST https://$DOMAIN/webhook/post-call"
}

# =============================================================================
# Main Installation Flow
# =============================================================================
main() {
    clear
    echo -e "${BLUE}"
    echo "  _____ _        _    ___  __  __ ____  "
    echo " | ____| |      / \  / _ \|  \/  / ___| "
    echo " |  _| | |     / _ \| | | | |\/| \___ \ "
    echo " | |___| |___ / ___ \ |_| | |  | |___) |"
    echo " |_____|_____/_/   \_\___/|_|  |_|____/ "
    echo ""
    echo " + OpenMemory Installation Script"
    echo -e "${NC}"
    echo ""

    # Check if running as root
    check_root

    # Gather configuration
    gather_config

    # Run installation steps
    install_base
    configure_firewall
    install_python
    install_nodejs
    install_nginx
    install_certbot
    setup_elaoms
    setup_openmemory
    setup_dashboard
    create_services
    get_ssl_certificate
    start_services
    verify_installation
    print_summary
}

# Run main function
main "$@"
