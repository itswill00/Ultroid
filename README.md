# Ultroid Optimized

A high-performance, security-audited fork of the Ultroid userbot. Designed for zero-gimmick execution and technical efficiency.

## Core Technical Optimizations

### Database & State
- **Unified KV Schema**: Migrated from column/collection-per-key schemas to centralized key-value storage for SQL and MongoDB.
- **Config Cache**: Core configurations are cached in-memory via `ULT_CONFIG` to eliminate redundant DB IO.
- **Process Lifecycle**: Re-engineered `.restart` command for sub-second process recovery.

### Execution & Security
- **Optimized aexec**: Custom asynchronous execution logic for low-latency code evaluation.
- **Access Control**: Owner-lock enforced on all core system commands (Eval, Bash).
- **Background Handlers**: Non-blocking system logging and telemetry.

## Performance Curated Plugins
Only high-utility, professional tools are included. All gimmick/filler plugins have been removed.

- **PM Permit**: Direct DM gatekeeper.
- **AFK**: Automated status manager.
- **DevTools**: System and code inspectors.
- **SysManager**: Server metric tracking and auto-cleanup.
- **AdminTools**: Standardized group management.

## Installation

### Unix (Linux/WSL/VPS/Termux)
```bash
git clone https://github.com/itswill00/Ultroid
cd Ultroid
# Install dependencies
pip install -r requirements.txt
# Run
python3 -m pyUltroid
```

## Configuration
Configure via `.env` file.

| Variable | Description |
|:---------|:------------|
| `API_ID` | Telegram App ID |
| `API_HASH` | Telegram App Hash |
| `SESSION` | Telethon Session String |
| `COMMAND_LOGGER` | Optional: Log commands to channel |

---
**Ultroid Optimized** | Focused on Performance.
Original project by TeamUltroid.
