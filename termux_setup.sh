#!/usr/bin/env bash
# ============================================================
#   Ultroid Optimized — Termux Quick Setup
#   This is a thin wrapper. The full logic lives in installer.sh
# ============================================================

set -euo pipefail

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
ok()   { echo -e "${G}[OK]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[ERROR]${N} $1"; exit 1; }

echo ""
echo "Ultroid Optimized — Termux Setup"
echo "──────────────────────────────────────"

# Verify we are actually in Termux
if [ ! -d "/data/data/com.termux/files/usr" ]; then
    fail "This script is intended for Termux only. Use installer.sh for other platforms."
fi

# Basic Termux bootstrap — only if python3 is not yet available
if ! command -v python3 &>/dev/null; then
    warn "Python not found. Bootstrapping..."
    pkg update -y && pkg install python git -y || fail "Cannot install python via pkg."
fi

ok "Termux environment confirmed."
echo ""

# Delegate to the main installer
bash installer.sh
