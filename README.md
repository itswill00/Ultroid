<p align="center">
    <a href="https://github.com/itswill00/Ultroid">
        <img src="https://graph.org/file/54a917cc9dbb94733ea5f.jpg" width="150" height="150" alt="Ultroid Logo">
    </a>
</p>

<h1 align="center">Ultroid [Optimized]</h1>

<p align="center">
    <strong>The Fastest, Cleanest, and Most Stable Ultroid Fork for Termux.</strong>
</p>

<p align="center">
    <a href="https://t.me/TeamUltroid">
        <img src="https://img.shields.io/badge/Telegram-Channel-blue.svg?style=for-the-badge&logo=telegram" alt="Telegram Channel">
    </a>
    <a href="https://t.me/UltroidSupportChat">
        <img src="https://img.shields.io/badge/Telegram-Support-red.svg?style=for-the-badge&logo=telegram" alt="Telegram Support">
    </a>
</p>

---

## 🚀 Why This Version?
Standard userbots are often heavy, slow to boot, and prone to installation errors on mobile devices due to complex dependencies like OpenCV or specialized C++ libraries. 

**Ultroid Optimized** is a surgical refinement of the original project, specifically tuned for **Termux (Android)** and low-resource environments. It focuses on **Zero Latency** and **Plug-and-Play** stability.

### ✨ Key Enhancements
- **⚡ Lightning Fast Boot:** Sequential async loading and deferred help-string processing reduce startup time by up to 70%.
- **🛠 Zero-Config LocalDB:** Automatically defaults to a high-performance local JSON database. No Redis, MongoDB, or SQL setup required.
- **🛡 Dependency-Lite Core:** Heavy and problematic modules (OpenCV, GingerIt, etc.) are disabled by default to ensure error-free installation on Termux.
- **📡 Instant-On Logic:** Bot becomes online immediately. Heavy tasks like log-channel checks and assistant customization run silently in the background.
- **📦 Offline-First Startup:** Removed automatic `git clone` and network operations during boot to prevent delays and "Flood Wait" errors.
- **🧩 Managed Addons:** Full support for external plugins with new in-chat toggle commands (`.addons on/off`).

---

## 🛠 Management Commands
Control your bot experience directly from any chat:

| Command | Description |
|---------|-------------|
| `.pmpermit on/off` | Toggle the DM security system. |
| `.addons on/off` | Enable/Disable external plugin loading. |
| `.a` / `.block` | Approve or Block users in private messages. |
| `.help [plugin]` | Get instant help (generated on-demand). |
| `.restart` | Safely reboot the bot to apply changes. |

---

## 📦 Quick Installation (Termux)

1. **Clone and Enter:**
   ```bash
   git clone https://github.com/itswill00/Ultroid
   cd Ultroid
   ```
2. **One-Click Setup:**
   ```bash
   bash installer.sh
   ```
3. **Generate Session:**
   ```bash
   python3 ssgen.py
   ```
4. **Launch:**
   ```bash
   python3 -m pyUltroid
   ```

---

## ⚙️ Configuration
This version is designed to run with minimal variables. Just set your `API_ID`, `API_HASH`, and `SESSION` in a `.env` file, and you are good to go. Everything else is handled automatically.

## 🤝 Credits
- **Original Project:** [TeamUltroid](https://github.com/TeamUltroid)
- **Optimizations:** [itswill00](https://github.com/itswill00)

---
<p align="center">
  Licensed under <a href="LICENSE">GNU Affero General Public License v3.0</a>
</p>
