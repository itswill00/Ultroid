<p align="center">
  <a href="https://github.com/itswill00/Ultroid">
    <img src="https://graph.org/file/54a917cc9dbb94733ea5f.jpg" width="140" height="140" style="border-radius:50%" alt="Ultroid Logo">
  </a>
</p>

<h1 align="center">Ultroid Optimized</h1>

<p align="center">
  <b>A Secure, Lightweight, and Cross-Platform Telegram Userbot.</b><br>
  <sub>Forked from <a href="https://github.com/TeamUltroid/Ultroid">TeamUltroid</a> · Security-Audited & Optimized</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Security-Audited-brightgreen?style=flat-square&logo=shield" alt="Security Audited">
  <img src="https://img.shields.io/badge/Platform-Termux%20|%20WSL%20|%20VPS%20|%20Docker-orange?style=flat-square" alt="Platforms">
  <img src="https://img.shields.io/github/last-commit/itswill00/Ultroid?style=flat-square" alt="Last Commit">
  <img src="https://img.shields.io/github/license/itswill00/Ultroid?style=flat-square" alt="License">
</p>

<p align="center">
  <a href="https://t.me/TeamUltroid">💬 Channel</a> &nbsp;·&nbsp;
  <a href="https://t.me/UltroidSupportChat">🆘 Support</a> &nbsp;·&nbsp;
  <a href="#-quick-installation">🚀 Installation</a> &nbsp;·&nbsp;
  <a href="#%EF%B8%8F-configuration">⚙️ Configuration</a> &nbsp;·&nbsp;
  <a href="#-faq--troubleshooting">❓ FAQ</a>
</p>

---

## ✨ What Makes This Fork Different?

| Feature | Ultroid Original | Ultroid Optimized |
|:--------|:---:|:---:|
| SQL Injection Protection | ❌ | ✅ Fixed |
| Eval/Bash Restriction | ❌ | ✅ Owner-only |
| Memory Leak (pmpermit) | ❌ | ✅ Resolved |
| Anti-Ban Rate Limiting | ❌ | ✅ gcast/gban/broadcast |
| Plugin Safety Scanner | ❌ | ✅ KEEP_SAFE filter |
| Hardcoded Platform Exclusions | ⚠️ All platforms | ✅ Per-platform |
| Duplicate Handler Prevention | ❌ | ✅ Guarded |
| Runtime `pip install` | ⚠️ Risky | ✅ Removed |

---

## 🔐 Security Features

- **Eval & Bash** commands are restricted to the account owner only (not sudo users)
- **SQL Injection Prevention** on all database operations
- **Plugin Channel Scanning** — plugins from channels are verified via KEEP_SAFE before loading
- **Rate Limiting** on all mass-action commands (`gcast`, `gban`, `broadcast`) to prevent account bans
- **Active Memory Management** on all long-running features

---

## 📦 Quick Installation

Choose your platform:

<details open>
<summary><b>📱 Termux (Android)</b></summary>

```bash
# 1. Install system dependencies
pkg update -y && pkg install git python -y

# 2. Clone the repo
git clone https://github.com/itswill00/Ultroid
cd Ultroid

# 3. Auto setup (handles Termux-specific dependencies)
bash termux_setup.sh

# 4. Generate your session
python3 ssgen.py

# 5. Start the bot
bash run.sh
```

> 💡 **Tip:** Run `termux-wake-lock` to keep the bot alive when the screen is off.

</details>

<details>
<summary><b>🪟 WSL / Ubuntu / Debian / VPS</b></summary>

```bash
# 1. Install system dependencies
sudo apt update && sudo apt install git python3 python3-venv ffmpeg -y

# 2. Clone the repo
git clone https://github.com/itswill00/Ultroid
cd Ultroid

# 3. Create a virtual environment (required on Ubuntu 22.04+)
python3 -m venv venv
source venv/bin/activate

# 4. Install Python packages
pip install -r requirements.txt

# 5. Generate your session
python3 ssgen.py

# 6. Start the bot
bash run.sh
```

> 💡 **Tip for VPS:** Use `screen` or `tmux` to keep the bot running after closing SSH:
> ```bash
> screen -S ultroid
> bash run.sh
> # Press Ctrl+A, D to detach
> ```

</details>

<details>
<summary><b>🐳 Docker</b></summary>

```bash
# Option 1: Plain Docker
docker build -t ultroid .
docker run -d --name ultroid --env-file .env ultroid

# Option 2: Docker Compose (recommended)
cp .env.sample .env
# Edit .env with your credentials
docker-compose up -d
```

> 💡 **View logs:** `docker logs -f ultroid`

</details>

<details>
<summary><b>🖥️ Windows (Native / PowerShell)</b></summary>

> ⚠️ Using **WSL** is strongly recommended for the best experience on Windows.

If you still want native Windows:
```powershell
# Install Git from https://git-scm.com and Python from https://python.org
git clone https://github.com/itswill00/Ultroid
cd Ultroid

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python -m pyUltroid
```

</details>

---

## ⚙️ Configuration

Copy the sample file and fill in your credentials:

```bash
cp .env.sample .env
nano .env   # or use your preferred editor
```

### Required Variables

| Variable | Description | How to Get |
|:---------|:------------|:-----------|
| `API_ID` | Your Telegram App ID | [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Your Telegram App Hash | [my.telegram.org](https://my.telegram.org) |
| `SESSION` | Your account login session string | Run `python3 ssgen.py` |

### Optional but Recommended

| Variable | Description |
|:---------|:------------|
| `BOT_TOKEN` | Assistant bot token (from [@BotFather](https://t.me/BotFather)) |
| `LOG_CHANNEL` | Channel/group ID to receive activity logs |
| `REDIS_URI` | Redis URI for cloud database (e.g. `redis://...`) |
| `REDIS_PASSWORD` | Redis password, if any |
| `MONGO_URI` | MongoDB URI as an alternative database |
| `GEMINI_API_KEY` | Google Gemini API key for AI features |
| `OPENAI_API_KEY` | OpenAI GPT API key |
| `ANTHROPIC_KEY` | Anthropic Claude API key |
| `SUDO_USERS` | Trusted user IDs (space-separated) |
| `LITE_DEPLOY` | Set `True` for lightweight mode (Termux / low-RAM) |

---

## 🚀 Running the Bot

Once configured, use the smart runner script which auto-detects your platform:

```bash
bash run.sh
```

Or run directly:
```bash
python3 -m pyUltroid
```

---

## 🛠️ Basic Commands

| Command | Function |
|:--------|:---------|
| `.ping` | Check if the bot is alive |
| `.help [plugin]` | Show help for a plugin |
| `.restart` | Safely restart the bot |
| `.update` | Update to the latest version |
| `.sysinfo` | System info (RAM, disk, uptime) |
| `.cleanup` | Clear temporary files |
| `.pmpermit on/off` | Toggle the DM guard system |
| `.addons on/off` | Toggle external plugin loading |
| `.a` / `.block` | Approve / Block a user in DMs |

---

## ❓ FAQ & Troubleshooting

<details>
<summary><b>❌ Error: externally-managed-environment (pip)</b></summary>

This appears on Ubuntu 22.04+ and WSL. The fix:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
</details>

<details>
<summary><b>❌ ModuleNotFoundError when starting the bot</b></summary>

Make sure your virtual environment is activated:
```bash
source venv/bin/activate   # Linux / WSL / Mac
.\venv\Scripts\activate    # Windows
```
Then reinstall:
```bash
pip install -r requirements.txt
```
</details>

<details>
<summary><b>❌ Session expired / invalid session</b></summary>

Regenerate your session string:
```bash
python3 ssgen.py
```
Then update the `SESSION=` value in your `.env` file.
</details>

<details>
<summary><b>❌ Bot stops on its own in Termux</b></summary>

1. Enable wake lock: open Termux and run `termux-wake-lock`
2. Or use the **Termux:Boot** add-on to auto-start the bot on device boot
</details>

<details>
<summary><b>❌ FloodWait / account getting rate-limited</b></summary>

This fork includes built-in rate limiting for all mass-action commands (`gcast`, `broadcast`, `gban`). If you still get limited, wait a few hours before using mass commands again.
</details>

<details>
<summary><b>⚠️ Bot is slow on Termux</b></summary>

Enable lightweight mode in `.env`:
```
LITE_DEPLOY=True
```
This will automatically disable heavy plugins.
</details>

---

## 🗂️ Project Structure

```
Ultroid/
├── pyUltroid/          # Core module (client, database, startup)
│   ├── startup/        # Bot initialization
│   ├── fns/            # Helper functions
│   └── dB/             # Database layer (Redis, Mongo, SQL, Local)
├── plugins/            # Main plugins (~80+ plugins)
├── assistant/          # Assistant bot plugins
├── resources/          # Strings and optional requirements
├── ssgen.py            # Session string generator
├── installer.sh        # Auto installer (Termux/VPS)
├── run.sh              # Smart runner (auto-detects platform)
└── .env.sample         # Configuration template
```

---

## 🤝 Contributing

Pull requests are welcome! Please make sure:
- Your code does not introduce new security vulnerabilities
- New plugins follow the existing patterns in `plugins/`
- Commit messages follow the format `type(scope): description`

---

## 📜 License

This project is licensed under the [GNU AGPL v3.0](LICENSE).

---

<p align="center">
  Built with ❤️ for the global Telegram community.<br>
  <sub>Original: <a href="https://github.com/TeamUltroid/Ultroid">TeamUltroid</a> · Forked &amp; Optimized by <a href="https://github.com/itswill00/Ultroid">itswill00</a></sub>
</p>
