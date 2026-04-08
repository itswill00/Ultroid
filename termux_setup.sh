#!/usr/bin/env bash
# Ultroid Termux Optimized Setup
# Designed for itswill00/Ultroid

echo "--- ULTROID TERMUX OPTIMIZER ---"
echo "Installing system dependencies..."

pkg update -y
pkg install python python-numpy python-pillow -y

echo "Installing Python libraries..."
pip install -r requirements.txt --no-cache-dir

# Pre-install some safe addons requirements
pip install pytz qrcode youtube-search-python --no-cache-dir

echo "Configuring Local Database..."
if [ ! -f .env ]; then
    cp .env.sample .env
    echo "LITE_DEPLOY=True" >> .env
    echo "HOSTED_ON=termux" >> .env
fi

echo "--- DONE ---"
echo "Use 'bash startup' to run the bot."
