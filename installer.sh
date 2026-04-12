#!/usr/bin/env bash
# ============================================================
#   Ultroid Optimized — Smart Installer v2
#   Platform-aware: Termux, Linux/VPS, WSL, Docker
#
#   Key behaviors:
#     - Skip packages that are already importable
#     - Termux: use pkg for C/Rust-heavy packages (pre-compiled ARM)
#     - Termux: use community pre-built wheels for pydantic-core
#     - Per-package install with failure isolation (one fail ≠ abort)
#     - Install DB drivers only if configured in .env
#     - Internet check before downloading
#     - Resume via .setup_state (re-run skips done steps)
#     - pkg update throttled to once per 24h
# ============================================================

set -uo pipefail   # Note: no -e, we handle errors per step

STATE_FILE=".setup_state"
REQ_FILE="requirements.txt"
OFFLINE=0

# ── Colors ────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
ok()   { echo -e "${G}[OK]${N}   $1"; }
info() { echo -e "${C}[..]${N}   $1"; }
warn() { echo -e "${Y}[!]${N}    $1"; }
fail() { echo -e "${R}[FAIL]${N} $1"; }
done_step() { grep -qx "$1" "$STATE_FILE" 2>/dev/null; }
mark_done() { echo "$1" >> "$STATE_FILE"; }

echo ""
echo "Ultroid Optimized — Setup"
echo "──────────────────────────────────────────────────"

# ── Platform Detection ────────────────────────────────────────
detect_platform() {
    if [ -d "/data/data/com.termux/files/usr" ]; then
        PLATFORM="termux"
    elif [ -f "/.dockerenv" ]; then
        PLATFORM="docker"
    elif [ -f "/proc/sys/fs/binfmt_misc/WSLInterop" ]; then
        PLATFORM="wsl"
    elif uname -s 2>/dev/null | grep -qi darwin; then
        PLATFORM="macos"
    else
        PLATFORM="linux"
    fi
    ok "Platform: ${PLATFORM}"
}

# ── Internet Check ────────────────────────────────────────────
check_internet() {
    info "Checking internet..."
    if curl -s --max-time 6 https://pypi.org > /dev/null 2>&1; then
        ok "Internet: online"
    else
        warn "Internet: offline or slow — using cached packages only"
        OFFLINE=1
    fi
}

# ── Python Check ──────────────────────────────────────────────
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
        fail "Python 3.10+ not found."
        echo "  Termux:  pkg install python"
        echo "  Linux:   sudo apt install python3.11"
        exit 1
    fi
    ok "Python: $($PYTHON --version)"
}

# ── Virtual Environment (non-Termux only) ─────────────────────
setup_venv() {
    [ "$PLATFORM" = "termux" ] && return

    if done_step "venv"; then
        # Just activate — don't skip silently
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate 2>/dev/null || true
        fi
        ok "venv: already set up"
        return
    fi

    if [ ! -d "venv" ]; then
        info "Creating virtual environment..."
        "$PYTHON" -m venv venv || { fail "venv creation failed"; return; }
    fi
    source venv/bin/activate
    pip install --quiet --upgrade pip 2>/dev/null
    ok "venv: ready"
    mark_done "venv"
}

# ── System Package Update (Termux, throttled) ─────────────────
termux_pkg_update() {
    [ "$PLATFORM" != "termux" ] && return
    done_step "pkg_update" && { ok "pkg: already updated recently"; return; }

    # Rate-limit: only update if stamp is older than 24h
    if [ -f ".pkg_updated" ] && [ "$(find .pkg_updated -mmin +1440 2>/dev/null | wc -l)" -eq 0 ]; then
        ok "pkg: update is fresh (< 24h), skipping"
        return
    fi

    info "Updating pkg (once every 24h)..."
    pkg update -y 2>/dev/null || warn "pkg update had warnings, continuing"
    touch .pkg_updated
    mark_done "pkg_update"
}

# ── System Libs & Build Tools ─────────────────────────────────
install_system_deps() {
    done_step "sys_deps" && { ok "System deps: done"; return; }
    info "Checking system dependencies..."

    if [ "$PLATFORM" = "termux" ]; then
        # Build tools (needed as fallback if some pkg fails)
        for dep in git clang make pkg-config; do
            command -v "$dep" &>/dev/null || pkg install "$dep" -y 2>/dev/null || true
        done

        # ffmpeg — required for audio/video features
        command -v ffmpeg &>/dev/null && ok "ffmpeg: present" \
            || { info "Installing ffmpeg..."; pkg install ffmpeg -y 2>/dev/null || warn "ffmpeg: failed (video features may not work)"; }

        # mediainfo — optional
        command -v mediainfo &>/dev/null && ok "mediainfo: present" \
            || pkg install mediainfo -y 2>/dev/null || true

        # Headers required for some pip C extensions as fallback
        for lib in libxml2 libxslt openssl; do
            pkg install "$lib" -y 2>/dev/null || true
        done

    elif command -v apt-get &>/dev/null; then
        NEEDED=""
        for dep in git ffmpeg mediainfo python3-pip python3-venv \
                   libxml2-dev libxslt1-dev libjpeg-dev zlib1g-dev \
                   libffi-dev libssl-dev; do
            dpkg -l "$dep" 2>/dev/null | grep -q "^ii" || NEEDED="$NEEDED $dep"
        done
        if [ -n "$NEEDED" ]; then
            info "apt-get install:$NEEDED"
            sudo apt-get install -y $NEEDED 2>/dev/null || warn "Some apt deps failed"
        else
            ok "System libs: all present"
        fi
    fi

    mark_done "sys_deps"
}

# ── Termux: Pre-built Packages via pkg ───────────────────────
#
# These packages require heavy C or Rust compilation when built
# from PyPI source. Termux provides pre-compiled ARM64 binaries.
# Always try pkg FIRST for these, before falling back to pip.
#
# Format: "pip_package_name:pkg_package_name:python_import_name"
#
TERMUX_PKG_MAP=(
    # Requires libxml2 + libxslt + compile time
    "lxml:python-lxml:lxml"

    # Requires libjpeg, libpng, zlib — very heavy to compile
    "Pillow:python-pillow:PIL"

    # Requires BLAS/LAPACK — huge compile, often OOM on phone
    "numpy:python-numpy:numpy"

    # Newer versions require Rust (rustls/ring crates)
    "cryptography:python-cryptography:cryptography"

    # C extension (libsodium) — used internally by telethon
    "PyNaCl:python-pynacl:nacl"

    # C extensions (multidict, yarl, frozenlist) — aiohttp deps
    # Try pkg version if available; otherwise pip may work via wheel
    "aiohttp:python-aiohttp:aiohttp"

    # C extension — Redis speedup
    "hiredis:python-hiredis:hiredis"

    # C extension — psutil for system monitoring plugin
    "psutil:python-psutil:psutil"
)

install_termux_prebuilt() {
    [ "$PLATFORM" != "termux" ] && return
    done_step "termux_prebuilt" && { ok "Termux pre-built packages: done"; return; }
    info "Installing pre-compiled packages via pkg..."

    for entry in "${TERMUX_PKG_MAP[@]}"; do
        pip_name="${entry%%:*}"
        rest="${entry#*:}"
        pkg_name="${rest%%:*}"
        import_name="${rest##*:}"

        if "$PYTHON" -c "import $import_name" 2>/dev/null; then
            ok "$pip_name: already importable"
            continue
        fi

        info "pkg install $pkg_name (pre-compiled)..."
        if pkg install "$pkg_name" -y 2>/dev/null; then
            ok "$pip_name: installed via pkg"
        else
            warn "$pip_name: pkg not available — will attempt pip later"
        fi
    done

    mark_done "termux_prebuilt"
}

# ── Termux: pydantic-core (Rust-based, needs special treatment) ─
#
# pydantic v2 uses pydantic-core (Rust). Cannot build from source:
#   - Android uses Bionic libc → linker errors
#   - OOM during Rust compilation on mobile
#   - No official ARM64 PyPI wheel for aarch64-android
#
# Community wheels exist at Eutalix/android-pydantic-core but only
# up to Python 3.12. Python 3.13+ → go straight to pydantic v1.
#
# IMPORTANT: always pass --only-binary=:all: so pip NEVER tries to
# compile from source. Without this, pip silently falls through to
# Rust build and hangs indefinitely.
#
install_termux_pydantic() {
    [ "$PLATFORM" != "termux" ] && return
    done_step "termux_pydantic" && { ok "pydantic-core: done"; return; }

    if "$PYTHON" -c "import pydantic_core" 2>/dev/null; then
        ok "pydantic-core: already installed"
        mark_done "termux_pydantic"
        return
    fi

    [ $OFFLINE -eq 1 ] && {
        warn "pydantic-core: offline — installing pydantic v1 (no network needed)"
        pip install "pydantic>=1.10,<2" --quiet 2>/dev/null \
            && ok "pydantic v1: installed" || fail "pydantic v1: failed"
        mark_done "termux_pydantic"
        return
    }

    # Get Python minor version to decide strategy
    PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 99)

    if [ "$PY_MINOR" -ge 13 ]; then
        # Eutalix community wheels only exist for Python <=3.12.
        # Attempting pip install on 3.13 causes pip to try Rust build → hangs.
        warn "Python 3.${PY_MINOR} detected — no ARM64 pydantic-core wheel available yet"
        warn "Using pydantic v1 (pure Python, fully compatible with groq>=1.9)"
        timeout 60 pip install "pydantic>=1.10,<2" --quiet 2>/dev/null \
            && ok "pydantic v1: installed" \
            || fail "pydantic v1: install failed"
        mark_done "termux_pydantic"
        return
    fi

    # Python <=3.12: try the community ARM64 pre-built wheel
    info "Python 3.${PY_MINOR}: trying community ARM64 pydantic-core wheel..."
    info "(This avoids Rust compilation entirely)"

    # --only-binary=:all: is CRITICAL — prevents pip from falling back to Rust source build
    # --timeout 30 limits the network request itself
    if timeout 90 pip install pydantic-core \
        --only-binary=:all: \
        --extra-index-url https://eutalix.github.io/android-pydantic-core/ \
        --timeout 30 \
        --quiet 2>/dev/null; then
        ok "pydantic-core: installed via ARM64 community wheel"
        mark_done "termux_pydantic"
        return
    fi

    # Wheel not found for this version either — fall back to pydantic v1
    warn "No compatible wheel found — falling back to pydantic v1"
    timeout 60 pip install "pydantic>=1.10,<2" --quiet 2>/dev/null \
        && ok "pydantic v1: installed as fallback" \
        || fail "pydantic: could not install any version"

    mark_done "termux_pydantic"
}


# ── pip Package Install (with skip + per-package error isolation) ─
#
# Packages that are known to have Termux compilation issues are
# handled via TERMUX_PKG_MAP above — so by the time we get here,
# they are either already installed or we pip-install as last resort.
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
    ["Pillow"]="PIL"
    ["numpy"]="numpy"
    ["cryptography"]="cryptography"
    ["PyNaCl"]="nacl"
    ["psutil"]="psutil"
    ["hiredis"]="hiredis"
)

# Packages to SKIP entirely on Termux (too heavy, no pkg equivalent)
# These will be noted as disabled features only.
SKIP_ON_TERMUX=(
    "torch"
    "torchvision"
    "tensorflow"
    "opencv-python"
    "scipy"
    "pandas"
)

# Version pins for Termux — newer versions pull C/Rust heavy deps.
# Format: "package_name:pinned_spec"
# Applied only on Termux, overrides the requirements.txt line.
TERMUX_VERSION_PINS=(
    # v5+  pulls curl_cffi (C extension, libcurl TLS, fails on Termux)
    # v3.x is pure Python + requests, works fine
    "duckduckgo_search:duckduckgo_search<5"

    # groq>=0.9 works with pydantic v1 (which we install instead of pydantic-core)
    # Pin to avoid resolution trying to force pydantic v2
    "groq:groq>=0.9,<1"

    # cloudscraper pulls newer cffi which may need compilation
    # pin to known working version
    "cloudscraper:cloudscraper==1.2.71"
)

install_pip_packages() {
    done_step "pip_packages" && { ok "pip packages: done"; return; }
    [ -f "$REQ_FILE" ] || { warn "$REQ_FILE not found"; return; }

    info "Installing Python packages (skipping already-installed)..."
    local failed=()

    while IFS= read -r line || [ -n "$line" ]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue

        if [[ "$line" == http* ]]; then
            _install_url_dep "$line"
            continue
        fi

        pkg_name=$(echo "$line" | sed 's/[>=<!;\[].*//' | tr -d '[:space:]')
        [ -z "$pkg_name" ] && continue

        # Skip on Termux if in the heavy-skip list
        if [ "$PLATFORM" = "termux" ]; then
            local skip=0
            for s in "${SKIP_ON_TERMUX[@]}"; do
                [ "$s" = "$pkg_name" ] && skip=1 && break
            done
            if [ $skip -eq 1 ]; then
                warn "$pkg_name: skipped on Termux (too heavy, feature disabled)"
                continue
            fi
        fi

        import_name="${IMPORT_MAP[$pkg_name]:-}"

        if [ -n "$import_name" ] && "$PYTHON" -c "import $import_name" 2>/dev/null; then
            ok "$pkg_name: installed (skip)"
            continue
        fi

        # On Termux, check if we have a version pin override for this package
        install_spec="$line"
        if [ "$PLATFORM" = "termux" ]; then
            for pin_entry in "${TERMUX_VERSION_PINS[@]}"; do
                pin_pkg="${pin_entry%%:*}"
                pin_spec="${pin_entry##*:}"
                if [ "$pin_pkg" = "$pkg_name" ]; then
                    install_spec="$pin_spec"
                    info "$pkg_name: using Termux version pin: $pin_spec"
                    break
                fi
            done
        fi

        info "Installing $pkg_name..."
        if _try_pip_install "$install_spec"; then
            ok "$pkg_name: installed"
        else
            failed+=("$pkg_name")
            fail "$pkg_name: failed — some features may not work"
        fi

    done < "$REQ_FILE"

    if [ ${#failed[@]} -gt 0 ]; then
        echo ""
        warn "Failed packages (non-fatal):"
        for p in "${failed[@]}"; do echo "    - $p"; done
        warn "The bot will start. Some features using these may error."
    fi

    mark_done "pip_packages"
}

# Install package — Termux-aware flags + global timeout
#
# timeout 180: hard wall-clock limit — kills pip if it hangs
# --timeout 30: limits individual network requests (download stall)
# --only-binary=:all: on Termux: NEVER fall through to source build
#   (source builds require compiler/Rust and hang indefinitely)
# Fallback chain: standard → --break-system-packages → return 1
#
_try_pip_install() {
    local spec="$1"
    if [ "$PLATFORM" = "termux" ]; then
        # Primary: binary-only, hard timeout
        timeout 180 pip install \
            --quiet \
            --only-binary=:all: \
            --timeout 30 \
            "$spec" 2>/dev/null && return 0

        # Some packages have no binary wheel but compile quickly (pure-C, no Rust)
        # Allow source build ONLY with a strict time limit
        timeout 120 pip install \
            --quiet \
            --break-system-packages \
            --timeout 30 \
            "$spec" 2>/dev/null && return 0

        return 1
    else
        timeout 300 pip install --quiet --timeout 60 "$spec" 2>/dev/null || return 1
    fi
}

# Install from URL (e.g. GitHub zip)
_install_url_dep() {
    local url="$1"

    # Telethon-Patch — check by module name
    if echo "$url" | grep -q "Telethon-Patch"; then
        if "$PYTHON" -c "import telethonpatch" 2>/dev/null; then
            ok "Telethon-Patch: installed (skip)"
            return
        fi
        [ $OFFLINE -eq 1 ] && { warn "Telethon-Patch: offline, skipping"; return; }
    fi

    info "URL dep: $(echo "$url" | sed 's|.*/\(.*\)/archive.*|\1|')"
    _try_pip_install "$url" && ok "URL dep: installed" || fail "URL dep: failed — $url"
}

# ── Optional DB Drivers (based on .env config) ───────────────
install_db_drivers() {
    done_step "db_drivers" && { ok "DB drivers: done"; return; }
    [ -f ".env" ] || { ok "No .env — using LocalDB, no extra drivers needed"; mark_done "db_drivers"; return; }

    source <(grep -v '^#' .env | grep -v '^\s*$' | grep '=' | head -50) 2>/dev/null || true

    local any=0

    if [ -n "${REDIS_URI:-}${REDIS_URL:-}" ]; then
        "$PYTHON" -c "import redis" 2>/dev/null && ok "redis: installed" || {
            info "REDIS_URI found — installing redis + hiredis..."
            _try_pip_install "redis" && ok "redis: done" || warn "redis: failed"
            _try_pip_install "hiredis" 2>/dev/null || true   # optional speedup
        }
        any=1
    fi

    if [ -n "${MONGO_URI:-}" ]; then
        "$PYTHON" -c "import pymongo" 2>/dev/null && ok "pymongo: installed" || {
            info "MONGO_URI found — installing pymongo..."
            _try_pip_install "pymongo[srv]" && ok "pymongo: done" || warn "pymongo: failed"
        }
        any=1
    fi

    if [ -n "${DATABASE_URL:-}" ]; then
        "$PYTHON" -c "import psycopg2" 2>/dev/null && ok "psycopg2: installed" || {
            info "DATABASE_URL found — installing psycopg2..."
            _try_pip_install "psycopg2-binary" && ok "psycopg2: done" || warn "psycopg2: failed"
        }
        any=1
    fi

    [ $any -eq 0 ] && ok "LocalDB mode — no extra drivers needed"
    mark_done "db_drivers"
}

# ── .env Setup ────────────────────────────────────────────────
setup_env() {
    if [ -f ".env" ]; then
        ok ".env: exists"
        return
    fi
    [ -f ".env.sample" ] || { warn ".env.sample missing"; return; }

    cp .env.sample .env
    [ "$PLATFORM" = "termux" ] && {
        # Set Termux defaults: handle empty values or placeholders
        sed -i 's/^LITE_DEPLOY=.*/LITE_DEPLOY=True/' .env
        sed -i 's/^HOSTED_ON=.*/HOSTED_ON=termux/' .env
    }

    ok ".env: created from sample"
    warn "Fill in API_ID, API_HASH, SESSION (or BOT_TOKEN) before starting"
    echo "    nano .env"
}

# ── Session Check ─────────────────────────────────────────────
check_session() {
    [ -f ".env" ] || return
    source <(grep -v '^#' .env | grep -v '^\s*$' | grep '=' | head -50) 2>/dev/null || true

    MODE="${RUNTIME_MODE:-dual}"

    if [ "$MODE" = "bot" ]; then
        [ -n "${BOT_TOKEN:-}" ] && ok "BOT_TOKEN: present" \
            || warn "BOT_TOKEN is empty (required for RUNTIME_MODE=bot)"
        return
    fi

    if [ -z "${SESSION:-}" ]; then
        echo ""
        warn "SESSION is not set"
        if [ -f "ssgen.py" ]; then
            read -r -p "  Generate session now? [y/N] " ans 2>/dev/null || ans="n"
            [[ "${ans,,}" = "y" ]] && "$PYTHON" ssgen.py
        else
            echo "  Run: python3 ssgen.py"
        fi
    else
        ok "SESSION: present"
    fi

    [ "$MODE" = "dual" ] && [ -z "${BOT_TOKEN:-}" ] && \
        warn "BOT_TOKEN not set — assistant bot and inline help won't work"
}

# ── Summary ───────────────────────────────────────────────────
print_summary() {
    echo ""
    echo "──────────────────────────────────────────────────"
    ok "Setup complete."
    echo ""
    echo "  Start:  bash run.sh"
    echo "  Or:     python3 -m pyUltroid"
    [ "$PLATFORM" != "termux" ] && echo "  (activate venv first: source venv/bin/activate)"
    echo ""
    echo "  Update: git pull && bash installer.sh"
    echo "──────────────────────────────────────────────────"
}

# ── Main Execution ────────────────────────────────────────────
detect_platform
check_internet
check_python
termux_pkg_update
install_system_deps
setup_venv
install_termux_prebuilt
install_termux_pydantic
install_pip_packages
install_db_drivers
setup_env
check_session
print_summary
