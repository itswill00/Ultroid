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

### Docker

```bash
docker build -t ultroid .
docker run --env-file .env ultroid
```

---

## Configuration

Create a `.env` file in the project root. All supported variables:

### Core (Required)

| Variable | Description |
|:---|:---|
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API Hash from my.telegram.org |
| `SESSION` | Telethon string session (required unless `RUNTIME_MODE=bot`) |
| `BOT_TOKEN` | Bot token from @BotFather (required for `bot` and `dual` modes) |
| `LOG_CHANNEL` | Telegram channel/chat ID for startup logs and alerts |

### Runtime Mode

| Variable | Values | Default |
|:---|:---|:---|
| `RUNTIME_MODE` | `dual` / `user` / `bot` | `dual` |

- **`dual`** — Both userbot and assistant bot are active. Commands handled by userbot (`.` prefix), inline/callback handled by bot.
- **`user`** — Userbot only. No separate bot is started. All output goes to log channel. `BOT_TOKEN` optional.
- **`bot`** — Bot only. No `SESSION` needed. All commands handled by bot (`BOT_TOKEN` required).

### Optional

| Variable | Description |
|:---|:---|
| `GROQ_API_KEY` | API key from console.groq.com for AI features |
| `HNDLR` | Command prefix (default: `.`) |
| `SUDO_HNDLR` | Prefix for sudo users (default: same as `HNDLR`) |
| `ADDONS` | Set `true` to load plugins from `addons/` folder |
| `REDIS_URI` | Redis connection URI (if using Redis as database) |
| `MONGO_URI` | MongoDB connection URI (if using MongoDB) |

---

## Restart and Update

```
.restart           — Restart the bot in place
.restart -u        — Pull latest commits, install new dependencies if any, then restart
```

The restart sequence:
1. Saves context (timestamp, version) to database
2. Fetches remote and applies changes if available
3. Detects merge conflicts — aborts and notifies if found
4. Disconnects both clients gracefully
5. Replaces process in-place via `os.execl`

After restart, the bot reports downtime duration and loaded plugin count.

---

## AI Features

Powered by Groq (Llama 3.3). Set `GROQ_API_KEY` in `.env` to enable.

```
.ask <question>           — Ask anything
.ask --search <query>     — Ask with real-time web search
.summarize                — Summarize a replied message
.tldr <count>             — Summarize last N messages in chat
.search <query>           — Direct web search results
.debug                    — Analyze bot logs for errors
.aimodel                  — View or switch active AI model
```

---

## System Monitoring

```
.sysmon          — CPU, RAM, disk, and network snapshot
.sysmon live     — Live update every 5s for 30s
.sysinfo         — Full system info (OS, Python, arch, uptime)
.pingcheck       — One-shot Telegram latency check
.pingwatch       — Monitor latency over time
```

---

## Database Backup

```
.backup          — Export all database keys to Log Channel as JSON
.restore         — Restore from a replied backup file (requires confirmation)
.dbinfo          — Show all database keys and count
```

---

## Session Security

```
.sessions        — List all active Telegram sessions on your account
.revoke <n>      — Revoke session number N
.revokeall       — Revoke all sessions except the current one
.sessionguard on — Enable new login monitoring (alerts to LOG_CHANNEL)
```

---

## Security Notes

- Never share your `.env` file or `SESSION` string.
- Sudo users can execute commands on your behalf — be selective.
- Sensitive DB keys (`SESSION`, `BOT_TOKEN`) are excluded from `.backup` exports.

---

*Ultroid Optimized — [github.com/itswill00/Ultroid](https://github.com/itswill00/Ultroid)*
