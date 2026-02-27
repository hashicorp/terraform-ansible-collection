#!/bin/bash

# Hashicorp Terraform Collection - Quick Start Setup Script
# This script sets up a complete development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Functions for output
print_header() {
    echo -e "\n${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if running in correct directory
if [ ! -f "galaxy.yml" ]; then
    print_error "This script must be run from the collection root directory"
    exit 1
fi

print_header "Hashicorp Terraform Collection - Setup"

# Step 1: Check Python
print_header "Step 1: Checking Python"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
print_info "Python version: $python_version"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
    print_error "Python 3.9+ required"
    exit 1
fi
print_success "Python version is compatible"

# Step 2: Create virtual environment
print_header "Step 2: Setting up Virtual Environment"

if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists, skipping creation"
else
    print_info "Creating virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate
print_success "Virtual environment activated"

# Step 3: Upgrade pip
print_header "Step 3: Upgrading pip"
pip install --upgrade pip --quiet
print_success "pip upgraded"

# Step 4: Install dependencies
print_header "Step 4: Installing Dependencies"

print_info "Installing production dependencies..."
pip install -r requirements.txt --quiet
print_success "Production dependencies installed"

print_info "Installing test/development dependencies..."
pip install -r test-requirements.txt --quiet
print_success "Test/development dependencies installed"

# Step 5: Install collection locally
print_header "Step 5: Installing Collection Locally"

print_info "Installing collection..."
ansible-galaxy collection install . --force --quiet
print_success "Collection installed"

# Step 6: Verify installation
print_header "Step 6: Verifying Installation"

if ansible-galaxy collection list | grep -q "hashicorp.terraform"; then
    print_success "Collection verified in Ansible"
else
    print_error "Collection not found after installation"
    exit 1
fi

# Step 7: Run validation
print_header "Step 7: Running Setup Validation"

if [ -f "scripts/validate_setup.py" ]; then
    python3 scripts/validate_setup.py
else
    print_warning "Setup validation script not found"
fi

# Final summary
print_header "Setup Complete! 🎉"

echo -e "${GREEN}Your development environment is ready!${NC}\n"

echo "Quick start commands:"
echo ""
echo "  ${BOLD}Unit Tests:${NC}"
echo "    make test-unit              # Run all unit tests"
echo "    make test-coverage          # Run tests with coverage report"
echo "    make test-unit-verbose      # Run tests with verbose output"
echo ""
echo "  ${BOLD}Code Quality:${NC}"
echo "    make lint_all               # Run all linting checks"
echo "    make fix_black              # Auto-format code"
echo "    make fix_isort              # Auto-fix imports"
echo ""
echo "  ${BOLD}Collection:${NC}"
echo "    make collection-docs        # View module documentation"
echo "    make collection-lint        # Run ansible-lint"
echo ""
echo "  ${BOLD}Development:${NC}"
echo "    make dev-loop               # Run tests + linting"
echo "    make help                   # Show all available targets"
echo ""
echo "For more information, see DEVELOPMENT.md"
echo ""
