# Ultroid: Natural Intelligence
<p align="center">
    <img src="https://img.shields.io/github/v/release/itswill00/Ultroid?style=flat-square&color=blue" alt="Release">
    <img src="https://img.shields.io/github/license/itswill00/Ultroid?style=flat-square&color=green" alt="License">
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Speed-Turbo_Mode-FF4500?style=flat-square&logo=speedtest" alt="Speed">
</p>

**A high-performance, minimalist Telegram userbot framework built for those who demand technical excellence and aesthetic precision.**

Ultroid is a professional-grade extension of your Telegram account. Designed to be lightweight and robust, it balances raw power with a "Zero-Gimmick" terminal-inspired aesthetic.

---

## 💎 Key Features

### 🚀 Turbo Media Engine (2026 Edition)
The industry's most aggressive downloader integration. Powered by a hardened `yt-dlp` core.
- **Auto-Detection**: Dropping a YouTube, TikTok, Instagram, or Twitter link in a group chat instantly triggers an interactive download prompt — no command needed.
- **Concurrent Fragments**: Multi-threaded extraction (up to 10 parallel streams) for 5x-10x faster downloads on VPS.
- **1MB Optimized Buffering**: Tuned for maximum disk throughput and high-speed network saturation.
- **Shadow Proxy Protocol**: Automatically bypasses Telegram's 50MB file size limit by relaying through a secure Assistant-Proxy, allowing for seamless delivery of files up to **2GB**.
- **Real-Time Control**: Interactive `[❌ Cancel]` buttons allow you to abort any active task instantly with automatic cleanup.
### 🧠 Advanced AI & Diagnostics
Deeply integrated large language models for productivity.
- **Llama 3.3 (Groq)**: Instant, high-context technical assistance.
- **Gemini Pro**: Precision coding diagnostics and world-class reasoning.
- **Indonesian Optimized**: AI Assistant is strictly tuned to respond in **Indonesian** (Bahasa Indonesia) for native Indonesian clarity.
- **Double-Box UI**: Professional, terminal-style Markdown output for all AI interactions.

---

## ⚡ Recent Enhancements (April 2026)

### 📦 Massive Plugin & Addon Collection
This repository is now fully synchronized with the official **TeamUltroid** ecosystem, featuring **150+ commands** across various categories.
- **Core Additions**: `_wspr`, `aiwrapper`, `audiotools`, `autopic`, `chatbot`, `echo`, `glitch`, `imagetools`, `logo`, `pdftools`, `qrcode`, and more.
- **45+ Premium Addons**: `anime`, `autoprofile`, `figlet`, `imdb`, `pokedex`, `quote`, `song`, `spam`, `wikipedia`, etc.
- **Zero-Config Deployment**: All dependencies are managed in `requirements.txt`.

### 🛠️ Fixed Instagram Downloader
- Integrated `SONZAIX_API_KEY` support to ensure stable Instagram media extraction on high-traffic servers.
- Optimized multi-threaded buffering for Reels, IGTV, and Carousel posts.

---

### 🛡️ Enterprise Security
- **Session Guard**: Real-time monitoring of account access and automatic revocation of suspicious session ghosts.
- **Tiered Authorization**: Dynamic multi-level permission system (Owner → Full Sudo → Scoped Sudo → Public) with sub-5-minute stale-cache invalidation.
- **Captcha Gateway**: Math-challenge verification prevents unauthorized public access to the assistant bot.

---

## ⚡ Quick Deployment

### Mobile Edition (Termux)
One-step installation for a native mobile experience:
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid && bash termux_setup.sh
```

### Production Environment (VPS / Linux)
Standard deployment for performance and stability:
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid
cp .env.sample .env && nano .env   # Fill in your credentials
bash installer.sh
```

### Docker (Containerized)
The most stable and reproducible deployment method:
```bash
cp .env.sample .env && nano .env   # Fill in your credentials
docker-compose up -d
```

---

## 📍 Essential Commands

| Category | Command | Description |
| :--- | :--- | :--- |
| **Media** | `.dl <url>` | Interactive download prompt (YT/TT/IG/TW/NSFW + universal). |
| **Media** | `.ytv <url>` | Direct video download, skips format prompt. |
| **Media** | `.yta <url>` | Direct audio (MP3) download, skips format prompt. |
| **Admin** | `.dlservice` | Toggle the autonomous group link-listener. |
| **AI** | `.ask <query>` | Context-aware AI technical search (Groq / Gemini). |
| **System** | `.health` | Real-time system diagnostics and memory audit. |
| **Sudo** | `.addsudo` | Add a sudo user (with optional scoped command list). |
| **Universal** | **Runs flawlessly on Mobile, VPS, and Local hosts.** | |

---

## ⚙️ Technical Requirements

| Component | Version | Purpose |
| :--- | :--- | :--- |
| Python | 3.10+ (3.12 recommended) | Core runtime |
| Node.js | 20+ | YouTube PoToken signature solver |
| FFmpeg | Any recent | Audio/video post-processing & merge |
| Git | Any | Auto-update support |

### YouTube on VPS
VPS IPs are commonly blocked by YouTube. You need **both** of these set in `.env`:
- `PO_TOKEN` — Proof of Origin token
- `VISITOR_DATA` — Client session context

See [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) to generate these.
A `cookies.txt` (Netscape format) exported from your browser provides additional authentication.

---

Ultroid — *Intelligence, beautifully simplified.*

---
Copyright (C) 2021-2026 TeamUltroid. Released under GNU Affero General Public License v3.0.
