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
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid
pip3 install -r requirements.txt
python3 -m pyUltroid
```

---

## 🛠️ Performance Architecture
Ultroid is built for the long haul.
- **Adaptive Runtime**: Choose between `User`, `Bot`, or `Dual` modes via `.env`.
- **Intelligent Caching**: Optimized database reads to save memory on low-tier VPS and Termux.
- **Atomic Persistence**: Restarts are instantaneous and clean—no ghost processes or hung sessions.

---

## 🧠 Advanced Intelligence
Powered by **Llama 3.3 (Groq)** with seamless **Gemini** failover.

- ` .ask ` — Specialized AI queries with real-time web search capabilities.
- ` .tldr ` — Intelligent chat summarization.
- ` .analyze ` — AI-powered AOSP/Kernel log diagnostics for developers.
- ` .summarize ` — Transform complex messages into concise points.

---

## 🛡️ Security & Monitoring
- **Group Intel**: Real-time surveillance and automated group protection with a minimalist alert system.
- **System Sentinel**: Live health monitoring and system diagnostics.
- **Session Guard**: Monitor active sessions and revoke unauthorized access instantly.
- **Scoped Sudo**: Granular permission control for authorized users.

---

## 📍 Command Overview
| Category | Key Commands |
| :--- | :--- |
| **System** | `.restart`, `.health`, `.sysmon`, `.sysinfo` |
| **AI** | `.ask`, `.tldr`, `.analyze`, `.aimodel` |
| **Security** | `.sessions`, `.revokeall`, `.sessionguard` |
| **Tools** | `.weather`, `.air`, `.exportnotes`, `.dbinfo` |

---

### 🌐 Connectivity
- **Primary Repo**: [github.com/itswill00/Ultroid](https://github.com/itswill00/Ultroid)
- **Support**: [@TeamUltroid](https://t.me/TeamUltroid)

*Ultroid — Intelligence, beautifully simplified.*

