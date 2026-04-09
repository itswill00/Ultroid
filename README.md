<p align="center">
    <a href="https://github.com/TeamUltroid/Ultroid">
        <img src="https://graph.org/file/54a917cc9dbb94733ea5f.jpg" width="150" height="150" alt="Ultroid Logo">
    </a>
</p>

<h1 align="center">Ultroid Userbot</h1>

<p align="center">
    <strong>The Most Powerful and Modular Telegram Userbot.</strong>
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

## 🌟 Introduction
**Ultroid** is a highly advanced, feature-rich, and stable Telegram userbot based on the Telethon library. It is designed to enhance your Telegram experience with automation, powerful management tools, and hundreds of interactive plugins. Whether you are an individual user or a group administrator, Ultroid provides the tools you need to stay in control.

## 🚀 Key Highlights
- **Multi-Platform Support**: Deployable on **Termux**, **Heroku**, **Docker**, **VPS**, and **Local machines**.
- **Hybrid Assistant Bot**: Seamlessly integrates a Bot API assistant for inline menus, callbacks, and management without losing user-mode power.
- **Smart PMPermit**: Advanced private message security to keep your DMs clean from spam and unwanted strangers.
- **Extensive Plugin Library**: Over 150+ built-in plugins for administration, media tools, AI wrappers, games, and more.
- **Addon Ecosystem**: Easily extend capabilities by loading external plugins from the [UltroidAddons](https://github.com/TeamUltroid/UltroidAddons) repository.
- **Universal Database**: Support for **Redis**, **MongoDB**, **SQL**, and **LocalDB** (JSON-based) for flexible and persistent storage.

## 🛠 Feature Categories
Ultroid is packed with tools categorized for every need:

### 🛡 Administration & Security
- **Admin Tools**: Promote, demote, ban, mute, and pin with ease.
- **Anti-Flood & Anti-Spam**: Protect your groups from automated attacks.
- **Locks**: Lock media, stickers, links, or specific message types.
- **Greetings & Goodbye**: Set custom welcome and farewall messages with media support.

### 📁 Media & Utilities
- **Converters**: Convert between audio/video formats, images, and stickers.
- **Download/Upload**: Download files from URLs or upload local files to Telegram.
- **PDF & Zip Tools**: Create and manage PDFs or Zip archives directly in chat.
- **G-Drive Integration**: Manage your Google Drive files right from your userbot.

### 🤖 AI & Automation
- **AI Wrappers**: Integration with various AI services for image generation and chat.
- **Auto-Pic & Auto-Bio**: Periodically update your profile picture or bio information.
- **Scheduled Messages**: Never miss a deadline or greeting with built-in scheduling.

### 🎮 Fun & Assistant
- **Inline Games**: Play interactive games via the assistant bot.
- **YouTube/Twitter Downloader**: Extract and download media from social platforms.
- **Custom Buttons**: Create your own inline keyboards and interactive messages.

## 📦 Quick Installation

### **Termux (Android)**
```bash
git clone https://github.com/itswill00/Ultroid
cd Ultroid
bash installer.sh
python3 -m pyUltroid
```

### **Manual (Linux/Windows)**
1. Install Python 3.9+
2. Clone the repository.
3. Install dependencies: `pip install -r requirements.txt`
4. Set environment variables (API_ID, API_HASH, SESSION).
5. Run: `python3 -m pyUltroid`

## ⚙️ Configuration
Ultroid uses environment variables or a `.env` file for configuration. Key variables include:
- `API_ID` & `API_HASH`: Get them from [my.telegram.org](https://my.telegram.org).
- `SESSION`: Generate using `python3 ssgen.py`.
- `BOT_TOKEN`: Token for your Assistant Bot from @BotFather.
- `LOG_CHANNEL`: ID of the channel where logs and backups will be sent.

## 🤝 Community & Support
- **Support Chat**: [@UltroidSupportChat](https://t.me/UltroidSupportChat)
- **Update Channel**: [@TeamUltroid](https://t.me/TeamUltroid)
- **Documentation**: [docs.ultroid.org](https://docs.ultroid.org)

---
<p align="center">
  Licensed under <a href="LICENSE">GNU Affero General Public License v3.0</a>
</p>
