<p align="center">
  <img src="./resources/extras/logo_readme.jpg" width="180" alt="Ultroid Logo">
</p>

<h1 align="center">Ultroid</h1>

<p align="center">
  <b>A simple, stable, and reliable Telegram Userbot.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/itswill00/Ultroid?style=flat-square&color=blue" alt="Release">
  <img src="https://img.shields.io/github/license/itswill00/Ultroid?style=flat-square&color=orange" alt="License">
  <a href="https://t.me/ultroid_next"><img src="https://img.shields.io/badge/Telegram-Join-blue?style=flat-square&logo=telegram" alt="Telegram"></a>
</p>

---

### What is Ultroid?
Ultroid is a personal assistant for your Telegram account. We focus on speed and ease of use, allowing you to extend features through addons without touching the core code.

### Environment Initialization
Choose the method that best fits your host:

**Remote Server / Linux Host**
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid
bash setup.sh
```

**Android Runtime (Termux)**
```bash
pkg update && pkg install python git -y
git clone https://github.com/itswill00/Ultroid && cd Ultroid
./setup.sh
```

**Update & Maintenance**
Keep your bot and configuration up-to-date:
```bash
bash sync.sh
```

---

### Basic Configuration
Ensure the following variables are set in your `.env` file:

| Variable | Usage |
| :--- | :--- |
| `API_ID` | API ID from my.telegram.org |
| `API_HASH` | API Hash from my.telegram.org |
| `SESSION` | Telethon Session String |
| `BOT_TOKEN` | Assistant bot token for inline features |
| `REDIS_URI` | Redis database URL |

---

### Key Features
- **Group Management:** Automated kick, ban, mute, and message purging.
- **AI Integration:** Chat with Groq or Gemini directly from your chat bar.
- **Media Tools:** Edit images, convert audio, and download videos from various platforms.
- **Addon Manager:** Install community features instantly with the `.install` command.
- **Resource Optimized:** Intelligent "Lite Mode" for low-RAM devices and older phones.

---

### Contribution & Support
Have an idea or found a bug? Feel free to open an **Issue** or submit a **Pull Request**.

*   **Telegram:** [@ultroid_next](https://t.me/ultroid_next)
*   **Maintenance:** [itswill00](https://github.com/itswill00)

---
<p align="center">License: AGPL-3.0</p>
