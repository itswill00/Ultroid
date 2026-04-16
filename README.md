# Ultroid: Natural Intelligence
**A high-performance, minimalist Telegram userbot framework built with a human-centric philosophy.**

Ultroid isn't just a bot; it's a modern, robust, and elegant extension of your Telegram account. Designed to be lightweight and professional, it balances raw power with a "Zero-Gimmick" aesthetic.

---

## 💎 Philosophy
- **Modern Aesthetics**: No rigid ASCII boxes. Clean Markdown, professional emojis, and minimalist layouts.
- **High Performance**: Optimized with Lazy TTL caching and efficient process management.
- **Human-Centric**: Designed to be readable, approachable, and stable.
- **Universal**: Runs flawlessly on Termux, Linux, VPS, and WSL.

---

## ⚡ Quick Start

### Termux (Android)
One-step installation optimized for mobile resources:
```bash
bash <(curl -L https://git.io/ultroid-termux)
```
*Or manual installation:*
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid && bash termux_setup.sh
```

### Linux / VPS / WSL
Optimized setup for high-performance deployments:
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid
bash installer.sh
```
*To start the bot:*
```bash
bash run.sh
```

---

## 🛠️ Performance Architecture
Ultroid is built for the long haul, operating on an **Enterprise-Grade** core framework.
- **Memory Leak Immunity**: Features a *Smart Timestamp Pruner* to prevent flood-waits and state collisions during massive bulk downloads.
- **Non-Blocking I/O**: Heavy tasks are offloaded natively without relying on slow `bash` subprocesses, ensuring the bot's event loop never freezes.
- **Atomic Persistence**: Restarts are instantaneous and clean—no ghost processes or hung sessions.

---

## ⏬ Universal Media Engine
Powered by deeply integrated `yt-dlp`, Ultroid features an ultra-discreet, zero-latency downloader.
- **Age-Gate & Geo Bypass**: Natively bypasses 18+ verification walls and regional ISP censorships without relying on flaky proxies.
- **Zero-Latency UI**: Instantaneous format selection (`1080p`, `720p`, `480p`, `Audio`) enforced entirely through backend arguments rather than slow network scrapes.
- **Discrete & Professional**: Seamlessly handles major Adult Hubs while masking the output behind professional UI tags (`[ 🔞 NSFW Media ]` or `[ 🌐 Universal Media ]`).
- **Assistant Proxy Separation**: All media processing is offloaded to the Assistant Bot, ensuring your main user account remains completely clean and immune to Telegram spam filters.

---

## 🧠 Advanced Intelligence
Powered by **Llama 3.3 (Groq)** with seamless **Gemini** failover.

- ` .ask ` — Specialized AI queries with real-time web search capabilities.
- ` .analyze ` — AI-powered code & log diagnostics for developers.
- ` .summarize ` — Transform complex messages into concise points.

---

## 🛡️ Security & Monitoring
- **Group Intel**: Real-time surveillance and automated group protection with a minimalist alert system.
- **Session Guard**: Monitor active sessions and revoke unauthorized access instantly.

---

## 📍 Command Overview
| Category | Key Commands |
| :--- | :--- |
| **System** | `.restart`, `.health`, `.sysmon`, `.sysinfo` |
| **Media Engine** | `.dl <url>`, `.yta <url>`, `.ytv <url>`, `.dlservice on` |
| **AI** | `.ask`, `.tldr`, `.analyze`, `.aimodel` |
| **Security** | `.sessions`, `.revokeall`, `.sessionguard` |

---

### 🌐 Connectivity
- **Primary Repo**: [github.com/itswill00/Ultroid](https://github.com/itswill00/Ultroid)
- **Support**: [@TeamUltroid](https://t.me/TeamUltroid)

*Ultroid — Intelligence, beautifully simplified.*

