#!/usr/bin/env bash
# ============================================================
#   Ultroid Smart Sync & Maintenance Engine (sync.sh)
#   Function: Code Update, Env Migration, & Asset Sync
# ============================================================

set -uo pipefail

# --- Technical UI Helpers ---
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
status() { echo -e "${C}[SYNC]${N} $1"; }
success() { echo -e "${G}[DONE]${N}  $1"; }
warning() { echo -e "${Y}[WARN]${N}  $1"; }
error() { echo -e "${R}[ERR]${N}   $1"; exit 1; }

echo -e "${C}Ultroid Synchronization Engine${N}"
echo "--------------------------------------------------"

# 1. Core Update
sync_code() {
    status "Synchronizing core repository..."
    if [ -d ".git" ]; then
        git stash > /dev/null 2>&1
        if git pull origin main --rebase > /dev/null 2>&1; then
            git stash pop > /dev/null 2>&1 || true
            success "Core: Up-to-date"
        else
            warning "Core: Pull failed (Network/Conflict). Check manually."
        fi
    else
        warning "Core: Not a git repository. Skipping update."
    fi
}

# 2. Environment Variable Migration
sync_env() {
    status "Synchronizing environment variables (.env)..."
    if [ ! -f ".env" ]; then
        if [ -f ".env.sample" ]; then
            cp .env.sample .env
            success "Config: .env generated from sample"
        else
            error ".env.sample missing. Cannot sync."
        fi
        return
    fi

    # Detect missing keys
    MISSING_KEYS=$(grep -v '^#' .env.sample | grep '=' | cut -d'=' -f1)
    ADDED=0

    for KEY in $MISSING_KEYS; do
        if ! grep -q "^$KEY=" .env; then
            DEFAULT_VAL=$(grep "^$KEY=" .env.sample | cut -d'=' -f2-)
            echo -e "${Y}[NEW]${N} Variable detected: ${C}$KEY${N}"
            read -p "      Enter value (Default: $DEFAULT_VAL): " USER_VAL
            FINAL_VAL=${USER_VAL:-$DEFAULT_VAL}
            echo "$KEY=$FINAL_VAL" >> .env
            ADDED=$((ADDED + 1))
        fi
    done

    if [ $ADDED -gt 0 ]; then
        success "Config: $ADDED new variables injected."
    else
        success "Config: No new variables detected."
    fi
}

# 3. Runtime & Asset Sync
sync_assets() {
    status "Synchronizing runtime assets..."
    
    # Refresh setup logic (Dependencies & Venv)
    if [ -f "setup.sh" ]; then
        bash setup.sh
    else
        error "setup.sh missing. Environment cannot be synced."
    fi
}

# 4. Final Cleanup
finalize() {
    chmod +x setup.sh sync.sh 2>/dev/null || true
    echo "--------------------------------------------------"
    success "Synchronization finalized."
    echo ""
    echo -e "  Execute: ${G}python3 -m pyUltroid${N}"
    echo ""
}

# --- Execution ---
sync_code
sync_env
sync_assets
finalize
