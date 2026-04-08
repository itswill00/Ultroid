<p align="center">
  <img src="./resources/extras/logo_readme.jpg" alt="TeamUltroid Logo">
</p>
<h1 align="center">
  <b>Ultroid - UserBot (Termux Optimized)</b>
</h1>

<b>A stable pluggable Telegram userbot, specially optimized for Termux (Android).</b>

[![](https://img.shields.io/badge/Ultroid-v2.1.2--Termux-blue)](#)
[![Forks](https://img.shields.io/github/forks/itswill00/Ultroid?style=flat-square&color=orange)](https://github.com/itswill00/Ultroid/fork)
[![Size](https://img.shields.io/github/repo-size/itswill00/Ultroid?style=flat-square&color=green)](https://github.com/itswill00/Ultroid/)   
[![Python](https://img.shields.io/badge/Python-v3.13+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-AGPL-blue)](https://github.com/itswill00/Ultroid/blob/main/LICENSE)

---

## ⚡ Why Choose This Fork?
This repository has been specifically modified to run perfectly on **Termux (Android)**:
- **Lightning Fast Startup**: Boots in only **~20 seconds**.
- **Memory Efficient**: Automatically uses local database (SQLite/JSON) to save RAM.
- **Crash Free**: Mass fixes for `AttributeError` (Telethon compatibility).
- **Anti-Hang**: Heavy library compilation (Rust/C++) is disabled by default to prevent device overheating.
- **Integrated Addons**: No need to redownload addons during every startup.

---

## 🚀 Quick Installation (Termux)
Just run this single command in your Termux:
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid && bash termux_setup.sh
```

### Run the Bot:
```bash
bash startup
```

---

## 🔧 Configuration Variables (.env)
For Termux users, you **DO NOT NEED** online MongoDB or Redis.
- `API_ID` & `API_HASH`: Get them at [my.telegram.org](https://my.telegram.org).
- `SESSION`: Your Telethon session string.
- `LITE_DEPLOY`: Set to `True` (Automatic via setup script).
- `HOSTED_ON`: Set to `termux`.

---

## 🛠 Troubleshooting (Termux)
- **`ChannelsTooMuchError`**: Your account has joined too many groups (limit 500). Please leave some old/inactive groups.
- **`FloodWait`**: Wait for a few seconds if Telegram limits your connection during startup.
- **Library Error**: If a plugin fails due to missing libraries, use `pip install <library-name>`. Avoid libraries requiring Rust compilation.

---

## 📜 License & Credits
Ultroid is licensed under the [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0.en.html) v3.
Thanks to [TeamUltroid](https://github.com/TeamUltroid) for the original codebase.

> Modified with ❤️ for Termux users by [@itswill00](https://github.com/itswill00).
