#!/bin/bash
#===============================================================================
# UFW Firewall Setup Script for ELAOMS
#===============================================================================
#
# Usage: sudo ./scripts/setup_firewall.sh
#
# This script configures UFW (Uncomplicated Firewall) for a secure production
# deployment of ELAOMS.
#
#===============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check for root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root or with sudo"
    exit 1
fi

log_info "Configuring UFW Firewall for ELAOMS..."

#-------------------------------------------------------------------------------
# Install UFW if not present
#-------------------------------------------------------------------------------
if ! command -v ufw &> /dev/null; then
    log_info "Installing UFW..."
    apt-get update
    apt-get install -y ufw
fi

#-------------------------------------------------------------------------------
# Reset to defaults
#-------------------------------------------------------------------------------
log_info "Resetting UFW to defaults..."
ufw --force reset

#-------------------------------------------------------------------------------
# Default policies
#-------------------------------------------------------------------------------
log_info "Setting default policies..."
ufw default deny incoming
ufw default allow outgoing

#-------------------------------------------------------------------------------
# SSH Access (CRITICAL - do this first!)
#-------------------------------------------------------------------------------
log_info "Allowing SSH access..."
ufw allow ssh
ufw allow 22/tcp comment 'SSH'

#-------------------------------------------------------------------------------
# HTTP/HTTPS for web traffic
#-------------------------------------------------------------------------------
log_info "Allowing HTTP and HTTPS..."
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

#-------------------------------------------------------------------------------
# Application port (optional - for direct access)
#-------------------------------------------------------------------------------
log_info "Allowing application port 8000..."
ufw allow 8000/tcp comment 'ELAOMS API'

#-------------------------------------------------------------------------------
# Optional: OpenMemory ports (if running locally)
#-------------------------------------------------------------------------------
# Uncomment if OpenMemory is on the same server
# log_info "Allowing OpenMemory ports..."
# ufw allow 8080/tcp comment 'OpenMemory API'
# ufw allow 3000/tcp comment 'OpenMemory Dashboard'

#-------------------------------------------------------------------------------
# Optional: Restrict SSH to specific IPs
#-------------------------------------------------------------------------------
# Uncomment and modify to restrict SSH access to specific IPs
# log_warn "Restricting SSH to specific IPs..."
# ufw delete allow ssh
# ufw delete allow 22/tcp
# ufw allow from 203.0.113.0/24 to any port 22 proto tcp comment 'SSH from office'
# ufw allow from 198.51.100.5 to any port 22 proto tcp comment 'SSH from admin'

#-------------------------------------------------------------------------------
# Enable firewall
#-------------------------------------------------------------------------------
log_info "Enabling UFW firewall..."
ufw --force enable

#-------------------------------------------------------------------------------
# Display status
#-------------------------------------------------------------------------------
echo ""
log_success "Firewall configured successfully!"
echo ""
ufw status verbose

echo ""
log_info "Current firewall rules:"
ufw status numbered

echo ""
log_info "To add additional rules:"
echo "  ufw allow <port>/tcp"
echo "  ufw allow from <ip> to any port <port>"
echo ""
log_info "To remove a rule:"
echo "  ufw status numbered"
echo "  ufw delete <number>"
