#!/usr/bin/env bash
# ============================================================
#   Ultroid Optimized — Smart Installer
#   Platform-aware: Termux, Linux/VPS, WSL, Docker
#   Features:
#     - Skip packages already installed
#     - Termux: prefer pkg over pip for heavy C-extension libs
#     - Per-package install with failure isolation
#     - DB driver install only if configured in .env
#     - Internet connectivity check before downloading
#     - Resume support via .setup_state
# ============================================================

set -euo pipefail

STATE_FILE=".setup_state"
REQ_FILE="requirements.txt"

# ── Colors ────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
ok()   { echo -e "${G}[OK]${N} $1"; }
info() { echo -e "${C}[..] $1${N}"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[FAIL]${N} $1"; }
done_step() { grep -qx "$1" "$STATE_FILE" 2>/dev/null; }
mark_done() { echo "$1" >> "$STATE_FILE"; }

# ── Platform Detection ────────────────────────────────────────
detect_platform() {
    if [ -d "/data/data/com.termux/files/usr" ]; then
        PLATFORM="termux"
    elif [ -f "/.dockerenv" ]; then
        PLATFORM="docker"
    elif [ -f "/proc/sys/fs/binfmt_misc/WSLInterop" ]; then
        PLATFORM="wsl"
    elif uname -s | grep -qi darwin; then
        PLATFORM="macos"
    else
        PLATFORM="linux"
    fi
    ok "Platform: ${PLATFORM}"
}

# ── Internet Check ────────────────────────────────────────────
check_internet() {
    info "Checking internet connectivity..."
    if curl -s --max-time 5 https://pypi.org > /dev/null 2>&1; then
        ok "Internet: connected"
    else
        warn "Internet: unreachable. Proceeding with cached/local packages only."
        OFFLINE=1
    fi
    OFFLINE=${OFFLINE:-0}
}

# ── Python Version Check ──────────────────────────────────────
check_python() {
    PYTHON=""
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            _maj=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)
            _min=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
            if [ "$_maj" -ge 3 ] && [ "$_min" -ge 10 ]; then
                PYTHON="$cmd"
                break
            fi
        fi
    done

    if [ -z "$PYTHON" ]; then
        fail "Python 3.10+ not found. Cannot continue."
        echo "  Install it first:"
        echo "    Termux: pkg install python"
        echo "    Linux:  sudo apt install python3.11"
        exit 1
    fi
    ok "Python: $($PYTHON --version)"
}

# ── Virtual Environment (non-Termux) ─────────────────────────
setup_venv() {
    [ "$PLATFORM" = "termux" ] && return  # Termux has no venv issues

    if done_step "venv"; then
        ok "venv: already set up (skipping)"
        source venv/bin/activate 2>/dev/null || true
        return
    fi

    if [ -d "venv" ]; then
        ok "venv: found existing environment"
    else
        info "Creating virtual environment..."
        "$PYTHON" -m venv venv
        ok "venv: created"
    fi

    source venv/bin/activate
    # Upgrade pip silently
    pip install --quiet --upgrade pip
    mark_done "venv"
}

# ── System Dependencies ───────────────────────────────────────
install_system_deps() {
    done_step "sys_deps" && { ok "System deps: already installed (skipping)"; return; }

    info "Installing system dependencies..."

    if [ "$PLATFORM" = "termux" ]; then
        # Only update if not done recently (check stamp file)
        if [ ! -f ".pkg_updated" ] || [ "$(find .pkg_updated -mmin +1440 2>/dev/null | wc -l)" -gt 0 ]; then
            info "Updating pkg (this may take a moment)..."
            pkg update -y 2>/dev/null && pkg upgrade -y 2>/dev/null || warn "pkg update had errors, continuing..."
            touch .pkg_updated
        fi

        # Required system libs
        for dep in git ffmpeg; do
            if ! command -v "$dep" &>/dev/null; then
                info "Installing $dep..."
                pkg install "$dep" -y 2>/dev/null || warn "Failed to install $dep"
            else
                ok "$dep: already installed"
            fi
        done

        # mediainfo is optional
        if ! command -v mediainfo &>/dev/null; then
            pkg install mediainfo -y 2>/dev/null || warn "mediainfo not installed (some features disabled)"
        fi

    elif command -v apt-get &>/dev/null; then
        sudo apt-get update -qq 2>/dev/null || warn "apt update failed"
        for dep in git ffmpeg mediainfo python3-pip python3-venv; do
            if ! dpkg -l "$dep" 2>/dev/null | grep -q "^ii"; then
                sudo apt-get install -y "$dep" 2>/dev/null || warn "Failed to install $dep"
            else
                ok "$dep: already installed"
            fi
        done
    fi

    mark_done "sys_deps"
}

# ── Termux: Pre-compiled Packages via pkg ────────────────────
#
# These packages require heavy C compilation if installed via pip.
# On Termux (ARM), pkg provides pre-built binaries — use them.
# Mapping: pip-name -> pkg-name -> import-name
#
TERMUX_PKG_MAP=(
    "lxml:python-lxml:lxml"
    "Pillow:python-pillow:PIL"
    "numpy:python-numpy:numpy"
    "cryptography:python-cryptography:cryptography"
)

install_termux_prebuilt() {
    [ "$PLATFORM" != "termux" ] && return

    done_step "termux_prebuilt" && { ok "Termux pre-built packages: done (skipping)"; return; }

    info "Installing pre-built packages via pkg (avoids heavy compilation)..."

    for entry in "${TERMUX_PKG_MAP[@]}"; do
        pip_name="${entry%%:*}"
        rest="${entry#*:}"
        pkg_name="${rest%%:*}"
        import_name="${rest##*:}"

        # Check if already importable
        if "$PYTHON" -c "import $import_name" 2>/dev/null; then
            ok "$pip_name: already importable (skip)"
            continue
        fi

        info "Installing $pip_name via pkg ($pkg_name)..."
        if pkg install "$pkg_name" -y 2>/dev/null; then
            ok "$pip_name: installed via pkg"
        else
            warn "$pip_name: pkg install failed, will try pip later"
        fi
    done

    mark_done "termux_prebuilt"
}

# ── Per-Package pip Install (with skip + retry logic) ─────────
#
# Map from requirements.txt name to Python import name.
# If import succeeds → skip. If pip fails → warn and continue.
#
declare -A IMPORT_MAP=(
    ["groq"]="groq"
    ["beautifulsoup4"]="bs4"
    ["duckduckgo_search"]="duckduckgo_search"
    ["lxml"]="lxml"
    ["telethon"]="telethon"
    ["gitpython"]="git"
    ["python-decouple"]="decouple"
    ["python-dotenv"]="dotenv"
    ["telegraph"]="telegraph"
    ["enhancer"]="enhancer"
    ["requests"]="requests"
    ["aiohttp"]="aiohttp"
    ["catbox-uploader"]="catbox"
    ["cloudscraper"]="cloudscraper"
    ["google-api-python-client"]="googleapiclient"
    ["oauth2client"]="oauth2client"
)

install_pip_packages() {
    done_step "pip_packages" && { ok "pip packages: already installed (skipping)"; return; }

    [ -f "$REQ_FILE" ] || { warn "$REQ_FILE not found, skipping pip installs"; return; }

    info "Checking and installing Python packages..."

    local failed_pkgs=()

    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and blank lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue

        # Handle GitHub URLs separately
        if [[ "$line" == http* ]]; then
            _install_url_dep "$line"
            continue
        fi

        # Strip version specifiers to get package name
        pkg_name=$(echo "$line" | sed 's/[>=<!].*//' | tr -d '[:space:]')
        [ -z "$pkg_name" ] && continue

        import_name="${IMPORT_MAP[$pkg_name]:-}"

        # If we know the import name, check if already importable
        if [ -n "$import_name" ]; then
            if "$PYTHON" -c "import $import_name" 2>/dev/null; then
                ok "$pkg_name: already installed (skip)"
                continue
            fi
        fi

        # Attempt to install
        info "Installing $pkg_name..."
        if _try_pip_install "$pkg_name"; then
            ok "$pkg_name: installed"
        else
            failed_pkgs+=("$pkg_name")
            fail "$pkg_name: installation failed (non-fatal, some features may be disabled)"
        fi

    done < "$REQ_FILE"

    if [ ${#failed_pkgs[@]} -gt 0 ]; then
        warn "The following packages failed to install:"
        for p in "${failed_pkgs[@]}"; do echo "  - $p"; done
        warn "Bot may still work. Check logs for missing import errors."
    fi

    mark_done "pip_packages"
}

# Install a single pip package — with Termux-specific flags
_try_pip_install() {
    local pkg="$1"
    if [ "$PLATFORM" = "termux" ]; then
        # --break-system-packages needed on Termux with newer pip
        pip install --quiet "$pkg" 2>/dev/null || \
        pip install --quiet --break-system-packages "$pkg" 2>/dev/null || \
        return 1
    else
        pip install --quiet "$pkg" 2>/dev/null || return 1
    fi
}

# Install from a URL (e.g. GitHub zip)
_install_url_dep() {
    local url="$1"

    # Special case: Telethon-Patch — check if already patched
    if echo "$url" | grep -q "Telethon-Patch"; then
        if "$PYTHON" -c "import telethonpatch" 2>/dev/null; then
            ok "Telethon-Patch: already installed (skip)"
            return
        fi
    fi

    info "Installing from URL: $url"
    if _try_pip_install "$url"; then
        ok "URL package installed"
    else
        fail "URL package failed: $url"
    fi
}

# ── Optional DB Drivers (based on .env) ──────────────────────
install_db_drivers() {
    done_step "db_drivers" && { ok "DB drivers: done (skipping)"; return; }

    [ -f ".env" ] || { info "No .env found — skipping optional DB drivers"; return; }

    # Load env vars silently
    source <(grep -v '^#' .env | grep -v '^\s*$' | grep '=') 2>/dev/null || true

    local installed=0

    if [ -n "${REDIS_URI:-}" ] || [ -n "${REDIS_URL:-}" ]; then
        if ! "$PYTHON" -c "import redis" 2>/dev/null; then
            info "Redis URI detected — installing redis driver..."
            _try_pip_install "redis" && _try_pip_install "hiredis" || warn "redis driver install failed"
        else
            ok "redis: already installed"
        fi
        installed=1
    fi

    if [ -n "${MONGO_URI:-}" ]; then
        if ! "$PYTHON" -c "import pymongo" 2>/dev/null; then
            info "MONGO_URI detected — installing pymongo..."
            _try_pip_install "pymongo[srv]" || warn "pymongo install failed"
        else
            ok "pymongo: already installed"
        fi
        installed=1
    fi

    if [ -n "${DATABASE_URL:-}" ]; then
        if ! "$PYTHON" -c "import psycopg2" 2>/dev/null; then
            info "DATABASE_URL detected — installing psycopg2..."
            _try_pip_install "psycopg2-binary" || warn "psycopg2 install failed"
        else
            ok "psycopg2: already installed"
        fi
        installed=1
    fi

    [ $installed -eq 0 ] && ok "LocalDB mode — no extra DB drivers needed"

    mark_done "db_drivers"
}

# ── .env Setup ────────────────────────────────────────────────
setup_env() {
    if [ -f ".env" ]; then
        ok ".env: already exists (skipping creation)"
        return
    fi

    if [ ! -f ".env.sample" ]; then
        warn ".env.sample not found — cannot auto-create .env"
        return
    fi

    cp .env.sample .env

    # Termux: set platform defaults
    if [ "$PLATFORM" = "termux" ]; then
        grep -q "LITE_DEPLOY" .env || echo "LITE_DEPLOY=True" >> .env
        grep -q "HOSTED_ON" .env || echo "HOSTED_ON=termux" >> .env
    fi

    ok ".env created from sample"
    echo ""
    warn "Open .env and fill in at minimum: API_ID, API_HASH, SESSION (or BOT_TOKEN)"
    echo "    nano .env"
}

# ── Session Check ─────────────────────────────────────────────
check_session() {
    [ -f ".env" ] || return

    source <(grep -v '^#' .env | grep -v '^\s*$' | grep '=') 2>/dev/null || true

    MODE="${RUNTIME_MODE:-dual}"

    if [ "$MODE" = "bot" ]; then
        [ -n "${BOT_TOKEN:-}" ] && ok "BOT_TOKEN: present" || warn "BOT_TOKEN is empty (required for RUNTIME_MODE=bot)"
        return
    fi

    if [ -z "${SESSION:-}" ]; then
        echo ""
        warn "SESSION is not set in .env"
        echo "  Generate one with: python3 ssgen.py"
        if [ -f "ssgen.py" ]; then
            read -r -p "  Run session generator now? [y/N] " ans
            [[ "${ans,,}" = "y" ]] && "$PYTHON" ssgen.py
        fi
    else
        ok "SESSION: present"
    fi
}

# ── Summary ───────────────────────────────────────────────────
print_summary() {
    echo ""
    echo "──────────────────────────────────────"
    ok "Setup complete."
    echo ""
    echo "  Start the bot:"
    [ "$PLATFORM" != "termux" ] && echo "    source venv/bin/activate"
    echo "    bash run.sh"
    echo "    # or: python3 -m pyUltroid"
    echo ""
    echo "  Update the bot:"
    echo "    git pull && bash installer.sh"
    echo "──────────────────────────────────────"
}

# ── Main ──────────────────────────────────────────────────────
echo ""
echo "Ultroid Optimized — Setup"
echo "──────────────────────────────────────"

detect_platform
check_internet
check_python
install_system_deps
setup_venv
install_termux_prebuilt
install_pip_packages
install_db_drivers
setup_env
check_session
print_summary
