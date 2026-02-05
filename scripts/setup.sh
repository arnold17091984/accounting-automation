#!/bin/bash
# =============================================================================
# Accounting Automation System - Setup Script
# =============================================================================
# Run this script to initialize the development or production environment
# Usage: ./scripts/setup.sh [dev|prod]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check Python (optional for local development)
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_info "Python version: $PYTHON_VERSION"
    else
        log_warn "Python 3 not found. You can still use Docker for Python scripts."
    fi

    log_info "Prerequisites check passed!"
}

# Setup environment file
setup_env() {
    log_info "Setting up environment file..."

    if [ -f "$PROJECT_DIR/.env" ]; then
        log_warn ".env file already exists. Skipping..."
        return
    fi

    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"

    # Generate encryption key
    ENCRYPTION_KEY=$(openssl rand -hex 32)
    sed -i.bak "s/<generate-with: openssl rand -hex 32>/$ENCRYPTION_KEY/" "$PROJECT_DIR/.env"

    # Generate webhook secret
    WEBHOOK_SECRET=$(openssl rand -hex 16)
    sed -i.bak "s/<generate-with: openssl rand -hex 16>/$WEBHOOK_SECRET/" "$PROJECT_DIR/.env"

    rm -f "$PROJECT_DIR/.env.bak"

    log_info ".env file created. Please edit it with your actual credentials."
    log_warn "IMPORTANT: Update the following in .env:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - ANTHROPIC_API_KEY"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - QB_CLIENT_ID and QB_CLIENT_SECRET"
}

# Setup Python virtual environment
setup_python_venv() {
    log_info "Setting up Python virtual environment..."

    if [ -d "$PROJECT_DIR/python/venv" ]; then
        log_warn "Virtual environment already exists. Skipping..."
        return
    fi

    if command -v python3 &> /dev/null; then
        cd "$PROJECT_DIR/python"
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        deactivate
        log_info "Python virtual environment created at python/venv/"
    else
        log_warn "Python 3 not available. Skipping virtual environment setup."
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating directory structure..."

    mkdir -p "$PROJECT_DIR/backups"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "/tmp/accounting-output"

    log_info "Directories created."
}

# Start services (development)
start_dev() {
    log_info "Starting development services..."

    cd "$PROJECT_DIR"
    docker-compose up -d

    log_info "Waiting for services to be ready..."
    sleep 10

    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        log_info "Services are running!"
        echo ""
        echo "Access n8n at: http://localhost:5678"
        echo "PostgreSQL is available at: localhost:5432"
        echo ""
    else
        log_error "Some services failed to start. Check logs with: docker-compose logs"
        exit 1
    fi
}

# Start services (production)
start_prod() {
    log_info "Starting production services..."

    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.prod.yml up -d

    log_info "Waiting for services to be ready..."
    sleep 15

    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_info "Production services are running!"
    else
        log_error "Some services failed to start. Check logs."
        exit 1
    fi
}

# Main
main() {
    MODE=${1:-dev}

    echo "============================================="
    echo " Accounting Automation System Setup"
    echo " Mode: $MODE"
    echo "============================================="
    echo ""

    check_prerequisites
    setup_env
    create_directories

    if [ "$MODE" == "dev" ]; then
        setup_python_venv
        start_dev
    elif [ "$MODE" == "prod" ]; then
        start_prod
    else
        log_error "Unknown mode: $MODE. Use 'dev' or 'prod'."
        exit 1
    fi

    echo ""
    log_info "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env with your actual credentials"
    echo "2. Access n8n and import workflows from n8n-workflows/"
    echo "3. Register Telegram bot with @BotFather"
    echo "4. Set up QuickBooks API at developer.intuit.com"
    echo ""
}

main "$@"
