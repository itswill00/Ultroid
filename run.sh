#!/usr/bin/env bash
# ============================================================
#   Ultroid Optimized — Runner Script
#   Supports: Termux, WSL, VPS, Docker
# ============================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Detect environment ---
detect_env() {
    if [ -d "/data/data/com.termux/files/usr" ]; then
        PLATFORM="Mobile Client"
    elif [ -f "/.dockerenv" ]; then
        PLATFORM="Containerized"
    elif [ -f "/proc/sys/fs/binfmt_misc/WSLInterop" ]; then
        PLATFORM="Integrated Host"
    else
        PLATFORM="Standard Server"
    fi
    echo "Platform: ${PLATFORM}"
}

# --- Check .env file ---
check_env_file() {
    if [ ! -f ".env" ]; then
        error ".env file not found. Run: cp .env.sample .env"
    fi

    # Load env vars for validation
    source <(grep -v '^#' .env | grep -v '^\s*$' | grep '=')

    # Determine RUNTIME_MODE (default: dual)
    MODE="${RUNTIME_MODE:-dual}"

    # SESSION required for user and dual mode
    if [ "$MODE" != "bot" ]; then
        if [ -z "$SESSION" ]; then
            error "SESSION is not set in .env (required for RUNTIME_MODE=${MODE})."$'\n'"       Run: python3 ssgen.py"
        fi
    fi

    # BOT_TOKEN required for bot and dual mode
    if [ "$MODE" = "bot" ] || [ "$MODE" = "dual" ]; then
        if [ -z "$BOT_TOKEN" ]; then
            warn "BOT_TOKEN is not set — required for RUNTIME_MODE=${MODE}."
        fi
    fi

    # API_ID and API_HASH always required
    if [ -z "$API_ID" ] || [ -z "$API_HASH" ]; then
        error "API_ID or API_HASH is missing in .env."
    fi

    info ".env validated (RUNTIME_MODE=${MODE})"
}

# --- Activate venv if present ---
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        info "Virtual environment activated."
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        info "Virtual environment activated (.venv)."
    fi
}

# --- Check Python version ---
check_python() {
    PYTHON_CMD=""
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            VER=$("$cmd" -c "import sys; print(sys.version_info.minor)")
            MAJ=$("$cmd" -c "import sys; print(sys.version_info.major)")
            if [ "$MAJ" -ge 3 ] && [ "$VER" -ge 10 ]; then
                PYTHON_CMD="$cmd"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        error "Python 3.10+ not found. Install it first."
    fi
    info "Python: $($PYTHON_CMD --version)"
}

# --- Run bot ---
run_bot() {
    echo ""
    echo "Starting Ultroid..."
    echo "──────────────────────────────"
    $PYTHON_CMD -m pyUltroid
}

# ─── Main ───────────────────────────────────────────────────
detect_env
check_env_file
activate_venv
check_python
run_bot
