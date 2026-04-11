#!/usr/bin/env bash
# ============================================================
#   Ultroid Optimized — Termux Auto-Setup
#   High-Performance Engine for Android Environment
# ============================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${GREEN}[>>] $1${NC}"; }
warn() { echo -e "${YELLOW}[!] $1${NC}"; }
err()  { echo -e "${RED}[X] $1${NC}"; exit 1; }

step "Updating system packages..."
pkg update -y && pkg upgrade -y || warn "Pkg update failed, trying to continue..."

step "Installing system dependencies..."
pkg install git python ffmpeg libxml2 libxslt -y || err "Critical dependency failure!"

# Optimized for Termux Python
pkg install python-numpy python-pillow -y || warn "Numpy/Pillow pkg failure, pip will handle it."

step "Installing requirements..."
# We need to compile lxml in termux sometimes, so we ensure static libs are ready
LDFLAGS="-L${PREFIX}/lib" CPPFLAGS="-I${PREFIX}/include" pip install --no-cache-dir lxml
pip install --no-cache-dir -r requirements.txt || err "Python requirements failed!"

step "Setting up environment..."
if [ ! -f .env ]; then
    cp .env.sample .env
    echo "LITE_DEPLOY=True" >> .env
    echo "HOSTED_ON=termux" >> .env
    echo -e "${YELLOW}Config file (.env) created.${NC}"
else
    warn ".env already exists, skipping creation."
fi

step "Installation Successful!"
echo -e "\nNext steps:"
echo -e "  1. ${YELLOW}nano .env${NC}          — Fill API_ID, API_HASH, SESSION"
echo -e "  2. ${YELLOW}python3 ssgen.py${NC}   — Generate session if needed"
echo -e "  3. ${YELLOW}bash run.sh${NC}        — Start the engine"
echo ""
