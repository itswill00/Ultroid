#!/usr/bin/env bash

# Ultroid Optimized Installer
# Tuned for Termux, WSL, and VPS

CURRENT_DIR="$(pwd)"
ENV_FILE_PATH=".env"
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Colors for better UI
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}      Ultroid Optimized Setup          ${NC}"
echo -e "${BLUE}=======================================${NC}"

# Detect Environment
if [ -d "/data/data/com.termux/files/usr" ]; then
    OS="Termux"
elif [ -f "/proc/sys/fs/binfmt_misc/WSLInterop" ]; then
    OS="WSL"
else
    OS="Linux/VPS"
fi

echo -e "${YELLOW}Detected Environment: ${OS}${NC}"

check_core_deps() {
    echo -e "${BLUE}Checking system dependencies...${NC}"
    DEPS="git python3 ffmpeg mediainfo"
    if [ "$OS" == "Termux" ]; then
        pkg update -y && pkg upgrade -y
        pkg install $DEPS -y
    elif command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y python3-pip python3-venv $DEPS -y
    fi
}

setup_venv() {
    # Handle PEP 668 (externally-managed-environment)
    if [ "$OS" != "Termux" ]; then
        if [ ! -d "venv" ]; then
            echo -e "${YELLOW}Creating Virtual Environment (Venv)...${NC}"
            python3 -m venv venv
        fi
        echo -e "${GREEN}Activating Virtual Environment...${NC}"
        source venv/bin/activate
    fi
}

install_python_deps() {
    echo -e "${BLUE}Installing Python Requirements...${NC}"
    pip install --upgrade pip
    
    # Try installing normally, fallback to --break-system-packages ONLY if absolutely necessary and not in venv
    if [ "$OS" == "Termux" ]; then
        pip install -r requirements.txt
    else
        pip install -r requirements.txt
    fi
    
    # Optional DB Requirements based on .env if exists
    if [ -f ".env" ]; then
        if grep -q "REDIS_URI" .env; then
            pip install redis hiredis
        fi
        if grep -q "MONGO_URI" .env; then
            pip install pymongo[srv]
        fi
        if grep -q "DATABASE_URL" .env; then
            pip install psycopg2-binary
        fi
    fi
}

finish() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${GREEN}Setup Completed Successfully!${NC}"
    echo -e "${YELLOW}Next Steps:${NC}"
    if [ "$OS" != "Termux" ]; then
        echo -e "1. Run: ${CYAN}source venv/bin/activate${NC}"
    fi
    echo -e "2. Run: ${CYAN}python3 ssgen.py${NC} (if you don't have a session)"
    echo -e "3. Run: ${CYAN}python3 -m pyUltroid${NC}"
    echo -e "${BLUE}=======================================${NC}"
}

# Execution
check_core_deps
setup_venv
install_python_deps
finish
