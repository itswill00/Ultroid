#!/usr/bin/env bash
# ============================================================
#   Ultroid Optimized — Smart Runner Script
#   Mendeteksi platform dan menjalankan bot dengan benar
# ============================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo "  ██╗   ██╗██╗  ████████╗██████╗  ██████╗ ██╗██████╗ "
    echo "  ██║   ██║██║  ╚══██╔══╝██╔══██╗██╔═══██╗██║██╔══██╗"
    echo "  ██║   ██║██║     ██║   ██████╔╝██║   ██║██║██║  ██║"
    echo "  ██║   ██║██║     ██║   ██╔══██╗██║   ██║██║██║  ██║"
    echo "  ╚██████╔╝███████╗██║   ██║  ██║╚██████╔╝██║██████╔╝"
    echo "   ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝ "
    echo -e "${NC}"
    echo -e "${GREEN}        Ultroid Optimized — Smart Runner${NC}"
    echo -e "─────────────────────────────────────────"
}

# --- Detect environment ---
detect_env() {
    if [ -d "/data/data/com.termux/files/usr" ]; then
        ENV_TYPE="Termux"
    elif [ -f "/proc/sys/fs/binfmt_misc/WSLInterop" ]; then
        ENV_TYPE="WSL"
    elif [ -f "/.dockerenv" ]; then
        ENV_TYPE="Docker"
    else
        ENV_TYPE="VPS/Linux"
    fi
    echo -e "${YELLOW}Platform: ${ENV_TYPE}${NC}"
}

# --- Check .env file ---
check_env_file() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}[ERROR] File .env tidak ditemukan!${NC}"
        echo -e "Jalankan: ${CYAN}cp .env.sample .env${NC} lalu isi variabelnya."
        exit 1
    fi

    # Check required vars
    source <(grep -v '^#' .env | grep -v '^\s*$')
    if [ -z "$API_ID" ] || [ -z "$API_HASH" ] || [ -z "$SESSION" ]; then
        echo -e "${RED}[ERROR] API_ID, API_HASH, atau SESSION belum diisi di .env!${NC}"
        echo -e "Jalankan: ${CYAN}python3 ssgen.py${NC} untuk membuat SESSION."
        exit 1
    fi
    echo -e "${GREEN}[OK] Konfigurasi .env valid.${NC}"
}

# --- Activate venv if exists (WSL/VPS) ---
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo -e "${GREEN}[OK] Virtual environment aktif.${NC}"
    fi
}

# --- Check Python version ---
check_python() {
    PYTHON_CMD=""
    for cmd in python3 python; do
        if command -v $cmd &>/dev/null; then
            VER=$($cmd -c "import sys; print(sys.version_info.minor)")
            if [ "$VER" -ge 10 ]; then
                PYTHON_CMD=$cmd
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        echo -e "${RED}[ERROR] Python 3.10+ tidak ditemukan!${NC}"
        exit 1
    fi
    echo -e "${GREEN}[OK] Python: $($PYTHON_CMD --version)${NC}"
}

# --- Run bot ---
run_bot() {
    echo -e ""
    echo -e "${GREEN}Menjalankan Ultroid...${NC}"
    echo -e "─────────────────────────────────────────"
    $PYTHON_CMD -m pyUltroid
}

# ─── Main ───────────────────────────────────────────────────
banner
detect_env
check_env_file
activate_venv
check_python
run_bot
