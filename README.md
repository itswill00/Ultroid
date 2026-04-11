# Ultroid Optimized (v3.0.0)

Ultroid Optimized is a professional, lightweight Telegram automation framework. This project is focused on high-performance execution, security, and a minimalist user experience for headless environments like Termux, Linux, and Docker.

---

## Features

- **AI Research**: Powered by Groq (Llama 3.3) for rapid information synthesis. Use the `--search` flag for real-time web research and context-aware answers.
- **Smart Sudo System**: Specialized permission architecture with a dedicated prefix (`!`). Command responses for sudoers are redirected to an Assistant Bot (@bot) to maintain the main account's privacy.
- **Security Hardening**: Includes a "Session Guard" to monitor active logins and strict access control for sensitive system commands.
- **Efficiency**: Optimized to run on low-RAM devices (Android/Termux and VPS), with a focus on non-blocking async execution.

---

## Installation

### 1. Termux (Android)
```bash
pkg update && pkg upgrade
pkg install git python -y
git clone https://github.com/itswill00/Ultroid
cd Ultroid
bash termux_setup.sh
```

### 2. Linux / VPS / WSL
```bash
git clone https://github.com/itswill00/Ultroid
cd Ultroid
pip3 install -r requirements.txt
python3 -m pyUltroid
```

### 3. Docker
```bash
docker build -t ultroid .
docker run --env-file .env ultroid
```

---

## Configuration (.env)

The following environment variables are supported in the `.env` file:

| Variable | Description | Requirement |
|:---|:---|:---|
| `API_ID` | Your API ID from my.telegram.org | Required |
| `API_HASH` | Your API Hash from my.telegram.org | Required |
| `SESSION` | Telethon String Session | Required |
| `BOT_TOKEN` | Token from @BotFather for Assistant Mode | Recommended |
| `GROQ_API_KEY` | API Key from console.groq.com | Optional |
| `LOG_CHANNEL` | ID for security alerts and crash logs | Recommended |
| `SUDO_HNDLR` | Prefix for sudo users (Default: `!`) | Optional |

---

## Security Notes
- Never share your `.env` file or `SESSION` string with anyone.
- Be cautious when adding Sudo users; they can execute commands on your behalf.
- The project follows a "Zero Gimmick" policy — keeping the interface technical and clutter-free.

---
*Ultroid Optimized v3.0.0 — Created by itswill00.*
