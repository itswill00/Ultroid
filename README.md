<p align="center">
  <img src="./resources/extras/logo_readme.jpg" width="180" alt="Ultroid Logo">
</p>

<h1 align="center">Ultroid</h1>

<p align="center">
  <b>Userbot Telegram yang simpel, stabil, dan bisa diandalkan.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/itswill00/Ultroid?style=flat-square&color=blue" alt="Release">
  <img src="https://img.shields.io/github/license/itswill00/Ultroid?style=flat-square&color=orange" alt="License">
  <a href="https://t.me/ultroid_next"><img src="https://img.shields.io/badge/Telegram-Join-blue?style=flat-square&logo=telegram" alt="Telegram"></a>
</p>

---

### Apa itu Ultroid?
Ultroid adalah asisten pribadi untuk akun Telegram Anda. Fokus utama kami adalah kecepatan dan kemudahan penggunaan. Anda bisa menambah fitur baru melalui addon tanpa harus mengutak-atik kode utama.

### Cara Pasang
Pilih metode yang paling cocok untuk Anda:

**Docker (Rekomendasi)**
```bash
git clone https://github.com/itswill00/Ultroid && cd Ultroid
# Atur variabel di .env
docker-compose up -d
```

**Termux**
```bash
pkg update && pkg install python git ffmpeg -y
git clone https://github.com/itswill00/Ultroid && cd Ultroid
./install-termux
```

**VPS / Linux**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -m pyUltroid
```

---

### Konfigurasi Dasar
Pastikan variabel berikut sudah terisi di `.env` Anda:

| Variabel | Kegunaan |
| :--- | :--- |
| `API_ID` | API ID dari my.telegram.org |
| `API_HASH` | API Hash dari my.telegram.org |
| `SESSION` | String sesi Telethon |
| `BOT_TOKEN` | Token bot untuk fitur asisten |
| `REDIS_URI` | URL database Redis |

---

### Fitur Unggulan
- **Manajemen Grup:** Kick, ban, mute, dan pembersihan pesan otomatis.
- **AI Integration:** Chatting dengan Groq atau Gemini langsung dari kolom chat.
- **Media Tools:** Edit gambar, konversi audio, dan download video dari berbagai platform.
- **Addon Manager:** Pasang fitur tambahan cukup dengan perintah `.install`.
- **Log Activity:** Pantau semua aktivitas bot melalui grup log khusus.

---

### Kontribusi & Support
Punya ide atau menemukan bug? Silakan buka **Issue** atau kirim **Pull Request**.

*   **Telegram:** [@ultroid_next](https://t.me/ultroid_next)
*   **Maintenance:** [itswill00](https://github.com/itswill00)

---
<p align="center">Lisensi: AGPL-3.0</p>
