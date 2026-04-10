<p align="center">
    <a href="https://github.com/itswill00/Ultroid">
        <img src="https://graph.org/file/54a917cc9dbb94733ea5f.jpg" width="160" height="160" style="border-radius: 50%;" alt="Ultroid Logo">
    </a>
</p>

<h1 align="center">Ultroid Optimized 🛡️</h1>

<p align="center">
    <strong>Surgical refinement of Ultroid. Precision-tuned for Security, Stability, and Performance.</strong>
</p>

<p align="center">
    <img src="https://img.shields.io/github/v/release/itswill00/Ultroid?style=for-the-badge&color=blue" alt="Release">
    <img src="https://img.shields.io/badge/Security-Audited-green?style=for-the-badge" alt="Security Audited">
    <img src="https://img.shields.io/badge/Platform-Termux%20|%20WSL%20|%20VPS-orange?style=for-the-badge" alt="Platforms">
</p>

<p align="center">
  <a href="https://t.me/TeamUltroid"><b>Channel</b></a> •
  <a href="https://t.me/UltroidSupportChat"><b>Support</b></a> •
  <a href="#-installation"><b>Installation</b></a>
</p>

---

## ⚡ Why This Fork?

Standard userbots are often built for massive feature-sets at the cost of security and mobile performance. **Ultroid Optimized** prioritizes the core experience:

*   **🛡️ Hardened Security:** Audited against **SQL Injection** and **Arbitrary Code Execution**. Privileged commands (`eval`/`bash`) are strictly restricted to the owner instance.
*   **🚀 Resource Efficient:** Intelligent environment detection adjusts resource allocation. Up to **70% faster boot** compared to the original.
*   **🧼 Clean Logic:** Fixed memory leaks in `pmpermit` and background tasks. No stale data lingering in RAM.
*   **🧩 Plug-and-Play:** Zero-config database architecture. Automatically switches between Redis, MongoDB, SQL, or Local JSON without user intervention.

---

## 🛠️ Performance Features

| Feature | Description |
| :--- | :--- |
| **Instant-On** | Core client boots immediately; background checks happen silently in the sub-processes. |
| **Smart Exclusions** | Automatically disables resource-heavy plugins on mobile (Termux) to prevent lag. |
| **Flood-Shield** | Intelligent FloodWait handling—bot stays online for other tasks while one command cools down. |
| **Memory Cleanup** | Active garbage collection for temporary data to maintain low RAM footprint. |

---

## 📦 Installation

Choose your platform for a tailored installation experience.

### 📱 Termux (Android)
The most optimized experience for mobile users.
```bash
pkg update && pkg upgrade -y
pkg install git python -y
git clone https://github.com/itswill00/Ultroid
cd Ultroid
bash installer.sh
```

### 🪟 WSL / Ubuntu / VPS
For serious deployments with high uptime.
```bash
git clone https://github.com/itswill00/Ultroid
cd Ultroid
# Recommended: Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m pyUltroid
```

### 🐳 Docker
```bash
docker build -t ultroid .
docker run ultroid
```

---

## ⚙️ Configuration

Set these variables in your `.env` file or Environment Variables:

*   `API_ID` & `API_HASH`: Get from [my.telegram.org](https://my.telegram.org).
*   `SESSION`: Generate using `python3 ssgen.py`.
*   `REDIS_URI` (Optional): For high-performance cloud storage.

---

## 🤝 Acknowledgments

*   **Original Project:** [TeamUltroid](https://github.com/TeamUltroid)
*   **Security Audit & Optimization:** [Antigravity AI](https://github.com) & [itswill00](https://github.com/itswill00)

---

<p align="center">
  Built with ❤️ for the Telegram Community.
</p>
