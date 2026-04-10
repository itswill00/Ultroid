#!/usr/bin/env bash
# ============================================================
#   Ultroid Optimized — Termux Setup Script
#   Dioptimalkan untuk Android / Low-RAM Environment
# ============================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${GREEN}[>>] $1${NC}"; }
warn() { echo -e "${YELLOW}[!] $1${NC}"; }
err()  { echo -e "${RED}[X] $1${NC}"; exit 1; }

step "Memperbarui paket Termux..."
pkg update -y && pkg upgrade -y

step "Menginstal dependensi sistem..."
pkg install git python ffmpeg -y || err "Gagal install dependensi sistem!"

# python-pillow dan python-numpy lebih stabil dari pkg daripada pip di Termux
pkg install python-numpy python-pillow -y

step "Menginstal Python packages..."
pip install --no-cache-dir -r requirements.txt || warn "Beberapa package mungkin gagal, lanjutkan..."

step "Menginstal package tambahan..."
pip install --no-cache-dir pytz qrcode youtube-search-python || true

step "Menyiapkan konfigurasi..."
if [ ! -f .env ]; then
    cp .env.sample .env
    echo "LITE_DEPLOY=True" >> .env
    echo "HOSTED_ON=termux" >> .env
    echo -e "${YELLOW}File .env dibuat. Silakan edit dengan API_ID, API_HASH, dan SESSION Anda:${NC}"
    echo -e "  nano .env"
else
    warn "File .env sudah ada, tidak ditimpa."
fi

step "Selesai!"
echo ""
echo -e "Langkah selanjutnya:"
echo -e "  1. ${YELLOW}nano .env${NC}          — Isi API_ID, API_HASH, SESSION"
echo -e "  2. ${YELLOW}python3 ssgen.py${NC}   — (Jika belum punya session)"
echo -e "  3. ${YELLOW}bash run.sh${NC}        — Jalankan bot"
echo ""
