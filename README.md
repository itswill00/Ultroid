# Ultroid Optimized (Zero Gimmick)

A high-performance, security-hardened, and professional-grade fork of the Ultroid userbot. Designed for developers and power users who prioritize technical efficiency over visual clutter.

## Core Technical Philosophy

- **Zero Gimmick**: All decorative elements, emojis, and filler logic have been stripped to ensure a cold, minimalist, and direct interface.
- **Security First**: Integrated `KEEP_SAFE` safety scanner to prevent accidental execution of destructive commands or credential leakage.
- **Atomic Reliability**: Re-engineered startup sequences and error handling to ensure 24/7 stability in diverse environments (WSL, Termux, VPS).

## Core Technical Optimizations

### Database & State
- **Unified KV Schema**: Optimized key-value storage for SQL and MongoDB.
- **Config Cache**: Core configurations are cached in-memory via `ULT_CONFIG` to eliminate redundant DB I/O.
- **Process Lifecycle**: High-performance restart logic for minimal downtime.

### Performance & Security
- **Optimized aexec**: Custom asynchronous execution for low-latency code evaluation with security scanning.
- **Access Control**: Strict owner-lock enforced on system-level commands (Eval, Bash, Term).
- **Non-Blocking Logic**: All system logging and intensive tasks (like Session Monitoring) run as non-blocking background handlers.

## Professional Addons (New)

The toolset has been expanded with professional-grade addons:

- **Smart Reply & AI**: Contextual summarization (`.summarize`), conversation analysis (`.tldr`), and direct AI querying (`.ask`) via Groq (Llama 3.3).
- **System Monitoring**: Real-time CPU, RAM, Disk, and Network monitoring (`.sysmon`) with automatic fallback to `/proc` for Termux compatibility.
- **Session Guard**: Audit active sessions and receive real-time alerts on LOG_CHANNEL for any new login attempts.
- **Message Vault**: Secure, encrypted storage for important messages and media with label-based retrieval.
- **Log Watcher**: Automated background scanning of `ultroid.log` with auto-delivery of error traces to the log channel.
- **Latent Monitoring**: High-precision Telegram latency tracking and monitoring (`.pingwatch`).
- **Bulk Operations**: Advanced message purging and keyword-based cleanup tools.
- **Task Scheduling**: Integrated in-memory reminder system for task management.

## Installation

### Linux / WSL / VPS / Termux
```bash
git clone https://github.com/itswill00/Ultroid
cd Ultroid
# Install dependencies
pip install -r requirements.txt
# Optional: Better performance in Termux
# pkg install python-psutil
# Run
python3 -m pyUltroid
```

## Configuration

Configure via `.env` file or environment variables.

| Variable | Description |
|:---------|:------------|
| `API_ID` | Telegram App ID |
| `API_HASH` | Telegram App Hash |
| `SESSION` | Telethon Session String |
| `LOG_CHANNEL` | Required: Channel ID for security alerts and logs |
| `GROQ_API_KEY` | Optional: For AI features (.ask, .tldr, .summarize) |
| `COMMAND_LOGGER` | Optional: Log commands to channel |

---
**Ultroid Optimized** | Performance. Security. Zero Gimmicks.
Original project by TeamUltroid.
