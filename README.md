<p align="center">
  <img src="./resources/extras/logo_readme.jpg" alt="TeamUltroid Logo">
</p>
<h1 align="center">
  <b>Ultroid - Enhanced UserBot</b>
</h1>

<b>A stable pluggable Telegram userbot + Voice & Video Call music bot, based on Telethon.</b>

[![](https://img.shields.io/badge/Ultroid-v0.8-crimson)](#)
[![Stars](https://img.shields.io/github/stars/itswill00/Ultroid?style=flat-square&color=yellow)](https://github.com/itswill00/Ultroid/stargazers)
[![Forks](https://img.shields.io/github/forks/itswill00/Ultroid?style=flat-square&color=orange)](https://github.com/itswill00/Ultroid/fork)
[![Size](https://img.shields.io/github/repo-size/itswill00/Ultroid?style=flat-square&color=green)](https://github.com/itswill00/Ultroid/)   
[![Python](https://img.shields.io/badge/Python-v3.10+-blue)](https://www.python.org/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/itswill00/Ultroid/graphs/commit-activity)
[![License](https://img.shields.io/badge/License-AGPL-blue)](https://github.com/itswill00/Ultroid/blob/main/LICENSE)
----

# Deploy
- [Local Machine](#deploy-locally)
- [Termux](#deploy-on-termux)
- [Heroku](#deploy-to-heroku)

# Documentation 
[![Documentation](https://img.shields.io/badge/Documentation-Ultroid-blue)](http://ultroid.tech/)

---

## Deploy on Termux (Recommended)
Get the [Necessary Variables](#Necessary-Variables) and run:
```bash
pkg update && pkg upgrade
pkg install python git ffmpeg -y
git clone https://github.com/itswill00/Ultroid
cd Ultroid
bash install-termux
```

## Deploy Locally
### Traditional Method
- Get your [Necessary Variables](#Necessary-Variables)
- Clone the repository:    
`git clone https://github.com/itswill00/Ultroid.git`
- Go to the cloned folder:    
`cd Ultroid`
- Create a virtual env:      
`virtualenv -p /usr/bin/python3 venv`
`. ./venv/bin/activate`
- Install the requirements:      
`pip install -U -r requirements.txt`
- Generate your `SESSION`:
  `bash sessiongen`
- Fill your details in a `.env` file.
- Run the bot:
   `bash startup`

---
## Necessary Variables
- `SESSION` - SessionString for your accounts login session. 

One of the following database:
- **Redis** (Recommended)
  - `REDIS_URI` - Redis endpoint URL.
  - `REDIS_PASSWORD` - Redis endpoint Password.
- **MONGODB**
  - `MONGO_URI` - Get it from [mongodb](https://mongodb.com/atlas).

---

# Core Contributor Team (Original)
We are grateful to the original TeamUltroid for the amazing base project.

<table>
  <tr>
    <td align="center"><a href="https://github.com/xditya"><img src="https://avatars.githubusercontent.com/xditya" width="75px;" alt=""/><br/><sub><b>@xditya</b></sub></a></td>
    <td align="center"><a href="https://github.com/1danish-00"><img src="https://avatars.githubusercontent.com/1danish-00" width="75px;" alt=""/><br/><sub><b>@1danish_00</b></sub></a></td>
    <td align="center"><a href="https://github.com/buddhhu"><img src="https://avatars.githubusercontent.com/buddhhu" width="75px;" alt=""/><br/><sub><b>@buddhhu</b></sub></a></td>
    <td align="center"><a href="https://github.com/TechiError"><img src="https://avatars.githubusercontent.com/TechiError" width="75px;" alt=""/><br/><sub><b>@TechiError</b></sub></a></td>
  </tr>
</table>

# License
[![License](https://www.gnu.org/graphics/agplv3-155x51.png)](LICENSE)   
Ultroid is licensed under [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0.en.html) v3 or later.

---
# Credits
* [TeamUltroid](https://t.me/TeamUltroid) for the original codebase.
* [Lonami](https://github.com/LonamiWebs/) for [Telethon.](https://github.com/LonamiWebs/Telethon)
* [MarshalX](https://github.com/MarshalX) for [PyTgCalls.](https://github.com/MarshalX/tgcalls)

> Enhanced and Maintained with 💕 by itswill00.
