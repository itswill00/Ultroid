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
- **Concurrent Fragments**: Multi-threaded extraction (10 parallel streams) translates to 5x-10x faster downloads on VPS.
- **1MB Optimized Buffering**: Tuned for maximum disk throughput and high-speed network saturation.
- **Shadow Proxy Protocol**: Automatically bypasses Telegram's 50MB file size limit by relaying through a secure Assistant-Proxy, allowing for seamless delivery of files up to **2GB**.
- **Real-Time Control**: Interactive `[❌ Cancel]` buttons allow you to abort any active task instantly with automatic cleanup.

### 🧠 Advanced AI & Diagnostics
Deeply integrated large language models for productivity.
- **Llama 3.3 (Groq)**: Instant, high-context technical assistance.
- **Gemini Pro**: Precision coding diagnostics and world-class reasoning.
- **Double-Box UI**: Professional, terminal-style Markdown output for all AI interactions.

### 🛡️ Enterprise Security
- **Session Guard**: Real-time monitoring of account access and automatic revocation of suspicious session ghosts.
- **Access Control**: Dynamic authorization ensures only you and your admins can control high-impact tasks.

---

## ⚡ Quick Deployment

### Mobile Edition
One-step installation for a native mobile experience:
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid && bash termux_setup.sh
```

### Production Environment
Standard deployment for performance and stability:
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid
bash installer.sh
```

### Docker (Containerized)
The most stable and reproducible deployment method:
```bash
docker-compose up -d
```

---

## 📍 Essential Commands

| Category | Command | Description |
| :--- | :--- | :--- |
| **Media** | `.dl <url>` | Intelligent auto-detection for TT, IG, TW, YT. |
| **Admin** | `.dlservice` | Toggle the autonomous group listener. |
| **Logic** | `.ask <query>` | Context-aware AI technical search. |
| **System** | `.health` | Real-time system diagnostics and memory audit. |
| **Universal** | **Runs flawlessly on Mobile, Server, and Local hosts.** |

---

## ⚙️ Technical Requirements
- **Python 3.10+** (3.12 Recommended)
- **Node.js 20+** (Required for YouTube Po-Token Extractors)
- **Git**

Ultroid — *Intelligence, beautifully simplified.*

---
Copyright (C) 2021-2026 TeamUltroid. Released under GNU Affero General Public License v3.0.
