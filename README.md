# Ultroid Optimized

A self-hosted Telegram userbot framework built for efficiency and low-resource environments.
Runs on Termux (Android), Linux, VPS, and WSL.

---

## Requirements

- Python 3.11+
- A Telegram account
- `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
- A Telethon string session (generated via `python3 sessiongen.py`)

---

## Installation

### Termux (Android)

```bash
pkg update && pkg upgrade
pkg install git python -y
git clone https://github.com/itswill00/Ultroid
cd Ultroid
bash termux_setup.sh
```

### Linux / VPS / WSL

```bash
git clone https://github.com/itswill00/Ultroid
cd Ultroid
pip3 install -r requirements.txt
python3 -m pyUltroid
```

---

## Configuration

Create a `.env` file in the project root. All supported variables:

### Core (Required)

| Variable | Description |
| :--- | :--- |
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API Hash from my.telegram.org |
| `SESSION` | Telethon string session (required unless `RUNTIME_MODE=bot`) |
| `BOT_TOKEN` | Bot token from @BotFather (required for `bot` and `dual` modes) |
| `LOG_CHANNEL` | Telegram channel/chat ID for startup logs and alerts |

### Runtime Mode

| Variable | Values | Default |
| :--- | :--- | :--- |
| `RUNTIME_MODE` | `dual` / `user` / `bot` | `dual` |

- **`dual`** — Both userbot and assistant bot are active.
- **`user`** — Userbot only.
- **`bot`** — Assistant bot only.

### AI & Advanced

| Variable | Description |
| :--- | :--- |
| `GROQ_API_KEY` | Supports multiple keys (space-separated) for automatic rotation |
| `GEMINI_API_KEY` | Secondary AI failover provider (used if Groq is exhausted) |
| `HNDLR` | Command prefix (default: `.`) |
| `SUDO_SCOPE` | LocalDB key for command-level sudo authorization |

---

## Restart and Update

```text
.restart           — Atomic process replacement
.restart -u        — Pull latest commits and dependencies, then restart
```

**Restart Sequence:**

1. Saves runtime context and downtime marker to LocalDB.
2. Performs repository synchronization (if `-u` is used).
3. **Automatic Cleanup**: Deletes the old "Initiating" message to keep logs clean.
4. **Direct Execution**: Replaces the process immediately via `os.execl` to prevent hangs.
5. Sends a unified **Startup Card** with downtime metrics and version info.

---

## AI Features

Powered by Llama 3.3 (Groq) with seamless failover to Google Gemini.

```text
.ask <query>              — Standard AI query
.ask --search <query>     — Ask with real-time web search
.tldr <count>             — Summarize last N messages in chat
.summarize                — Summarize a replied message
.analyze                  — Analyze AOSP/Kernel logs (replied file)
.aimodel                  — View or switch active AI model
```

---

## AOSP Log Analysis

Professional diagnostic tools for Android developers. Supports `.log`, `.txt`, and `.gz` formats.

```text
.analyze                  — Automatically detects Logcat, Dmesg, and Build logs
.analyze <instruction>    — Analyze with specific prompts (e.g., "cari penyebab lmk")
```

*Outputs are rendered as professional Markdown reports on Telegraph.*

---

## System Monitoring

```text
.sysmon          — CPU, RAM, disk, and network snapshot
.sysmon live     # Live monitor mode (30s)
.sysinfo         — Full OS/Python/Architecture info
.pingcheck       — One-shot latency check
.pingwatch       — Real-time latency tracking
```

---

## Session Security

```text
.sessions        — List all active Telegram sessions
.revoke <n>      — Revoke a specific session
.revokeall       — Terminate all other sessions
.sessionguard on — Enable login monitoring alerts
```

---

## Security Notes

- Sudo users now support **Scoped Access**. You can authorize standard sudoers to use only specific commands (e.g., `.addsudo @user analyze`).
- Database backups (`.backup`) automatically exclude sensitive tokens and sessions.

---

*Ultroid Optimized — [github.com/itswill00/Ultroid](https://github.com/itswill00/Ultroid)*
