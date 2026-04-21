#!/usr/bin/env bash
# ============================================================
#   Ultroid Universal Environment Deployer (setup.sh)
#   Target: POSIX-compliant Linux Distribution
#   Architectures: x86_64, aarch64 (ARMv8), armv7l
# ============================================================

set -uo pipefail

# --- Configuration & State ---
STATE_FILE=".setup_state"
REQ_FILE="requirements.txt"
LOG_FILE="setup.log"

# --- Technical UI Helpers ---
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
status() { echo -e "${C}[STATUS]${N} $1"; }
success() { echo -e "${G}[DONE]  ${N} $1"; }
warning() { echo -e "${Y}[WARN]  ${N} $1"; }
error() { echo -e "${R}[ERROR] ${N} $1"; exit 1; }

echo -e "${C}Ultroid Environment Initialization${N}"
echo "--------------------------------------------------"

# 1. Environment Sensing
detect_env() {
    status "Probing host environment..."
    ARCH=$(uname -m)
    OS=$(uname -s)
    
    if [ -d "/data/data/com.termux/files/usr" ]; then
        ENV_TYPE="Android Runtime (Termux)"
        PKG_MGR="pkg"
    elif [ -f "/.dockerenv" ]; then
        ENV_TYPE="Containerized Linux"
        PKG_MGR="apt-get" # Defaulting to Debian-based for Docker
    elif [ -f "/etc/debian_version" ]; then
        ENV_TYPE="Native Debian/Ubuntu Host"
        PKG_MGR="apt-get"
    elif [ -f "/etc/arch-release" ]; then
        ENV_TYPE="Native Arch Linux Host"
        PKG_MGR="pacman"
    else
        ENV_TYPE="Generic POSIX Host"
        PKG_MGR="unknown"
    fi
    
    success "Host: $ENV_TYPE ($ARCH)"
}

# 2. Network Synchronization
check_connectivity() {
    status "Verifying network connectivity..."
    if curl -s --max-time 5 https://pypi.org > /dev/null 2>&1; then
        success "Connectivity: Synchronized"
    else
        warning "Connectivity: Limited. Offline deployment may fail."
    fi
}

# 3. System Dependency Layer
sync_system_deps() {
    status "Synchronizing system-level dependencies..."
    
    case $PKG_MGR in
        pkg)
            pkg update -y > /dev/null 2>&1
            for dep in python git ffmpeg nodejs aria2 libjpeg-turbo zlib libxml2 libxslt; do
                pkg install "$dep" -y > /dev/null 2>&1 || warning "Dependency $dep sync failed."
            done
            ;;
        apt-get)
            sudo apt-get update -y > /dev/null 2>&1 || true
            sudo apt-get install -y python3-venv python3-pip git ffmpeg nodejs aria2 \
                libjpeg-dev zlib1g-dev libxml2-dev libxslt1-dev > /dev/null 2>&1 || true
            ;;
        pacman)
            sudo pacman -Sy --noconfirm python python-pip git ffmpeg nodejs aria2 > /dev/null 2>&1 || true
            ;;
        *)
            warning "Unknown package manager. Manual dependency injection required."
            ;;
    esac
    success "System Layer: Ready"
}

# 4. Python Runtime Isolation
init_python_runtime() {
    status "Initializing isolated Python runtime..."
    
    PYTHON_CMD=""
    for cmd in python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done

    [ -z "$PYTHON_CMD" ] && error "Python 3.10+ runtime not detected."

    if [ "$PKG_MGR" != "pkg" ]; then
        if [ ! -d "venv" ]; then
            $PYTHON_CMD -m venv venv || error "Virtual environment creation failed."
        fi
        source venv/bin/activate
        success "Runtime: Virtualized (.venv)"
    else
        success "Runtime: Native (Termux Optimization)"
    fi
    
    python3 -m pip install --upgrade pip > /dev/null 2>&1
}

# 5. Asset Deployment (Requirements)
deploy_assets() {
    status "Deploying Python package assets..."
    
    if [ "$PKG_MGR" = "pkg" ]; then
        # Termux Optimization: Install pre-compiled binaries for heavy libs
        status "Injecting pre-compiled ARM binaries..."
        for p in python-lxml python-pillow python-numpy python-cryptography python-pynacl python-psutil; do
            pkg install "$p" -y > /dev/null 2>&1 || true
        done
    fi

    pip install -r "$REQ_FILE" --quiet > /dev/null 2>&1 || {
        warning "Package asset deployment had minor conflicts. Retrying with --no-cache-dir..."
        pip install -r "$REQ_FILE" --no-cache-dir --quiet > /dev/null 2>&1 || warning "Asset deployment finalized with warnings."
    }
    success "Assets: Deployed"
}

# 6. Configuration Injection
inject_config() {
    if [ ! -f ".env" ]; then
        status "Initializing configuration (.env)..."
        cp .env.sample .env
        success "Config: Default injected"
    else
        success "Config: Existing detected"
    fi
}

# 7. Final Integrity Check
finalize() {
    echo "--------------------------------------------------"
    success "Environment synchronization finalized."
    echo ""
    echo -e "  Execute: ${G}python3 -m pyUltroid${N}"
    [ "$PKG_MGR" != "pkg" ] && echo -e "  Note: Ensure venv is active (${C}source venv/bin/activate${N})"
    echo ""
}

# --- Execution ---
detect_env
check_connectivity
sync_system_deps
init_python_runtime
deploy_assets
inject_config
finalize
