# Ultroid Addon - KomikDewasa (NSFW/Owner-Only)
# Website: https://komikdewasa.art/
# Author: itswill00

import re
import base64
from bs4 import BeautifulSoup
from telethon import Button
from pyUltroid.fns.helper import run_async
from . import ultroid_cmd, udB, LOGS, asst, ultroid_bot, eor

# Google Focus Proxy to bypass direct image blocks
IMG_PROXY = "https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=2592000&url="

def encode_url(url):
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

def decode_url(data):
    padding = '=' * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode()

async def fetch_page(url):
    import httpx
    try:
        from urllib.parse import quote
        # Metode licik: Bypassing ISP & Cloudflare via CodeTabs
        proxy_url = f"https://api.codetabs.com/v1/proxy?quest={quote(url)}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            res = await client.get(proxy_url)
            if res.status_code == 200:
                return res.text
    except Exception as e:
        LOGS.error(f"KomikDewasa Fetch Error: {e}")
    return None

@ultroid_cmd(pattern="kd( (.*)|$)", owner_only=True)
async def komik_dewasa_search(event):
    query = event.pattern_match.group(1).strip()
    if not query:
        return await event.eor("`Gunakan: .kd <judul komik>`")

    xx = await event.eor("`Mencari komik di arsip...`")
    
    import httpx
    search_url = f"https://duckduckgo.com/html/?q=site:komikdewasa.art+{query}"
    try:
        r = httpx.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('a', class_='result__a', href=re.compile(r'komikdewasa\.art/'))
        
        if not results:
            return await xx.edit("`Komik tidak ditemukan atau akses diblokir.`")

        buttons = []
        for res in results[:8]: # Limit 8 results
            title = res.get_text()[:30] # Limit text length
            link = res['href']
            if "uddg=" in link:
                link = link.split("uddg=")[1].split("&")[0]
                from urllib.parse import unquote
                link = unquote(link)
            
            # Use callback to fetch chapters
            buttons.append([Button.inline(f"📖 {title}", data=f"kd_ch:{encode_url(link)}")])
        
        await xx.edit(f"**Hasil Pencarian: `{query}`**\nSilakan pilih komik untuk melihat chapter.", buttons=buttons)
    except Exception as e:
        await xx.edit(f"**Kesalahan:** `{e}`")

# --- Assistant Callbacks ---
if asst:
    from . import callback

    @callback(re.compile("kd_ch:(.*)"))
    async def kd_callback_chapters(event):
        # Access control: only owner can click
        if event.sender_id != ultroid_bot.uid:
            return await event.answer("Akses ditolak.", alert=True)
            
        raw_data = event.pattern_match.group(1).decode()
        url = decode_url(raw_data)
        
        await event.answer("Mengambil daftar chapter...", alert=False)
        html = await fetch_page(url)
        if not html:
            return await event.respond("Gagal mengambil data. Cloudflare memblokir akses.")

        soup = BeautifulSoup(html, 'html.parser' if 'lxml' not in str(BeautifulSoup) else 'lxml')
        chapters = soup.find_all('li', class_='wp-manga-chapter')
        
        if not chapters:
            return await event.edit("Chapter tidak ditemukan di link ini.")

        buttons = []
        for ch in chapters[:10]: # Show latest 10 chapters
            a_tag = ch.find('a')
            ch_link = a_tag['href']
            ch_name = a_tag.get_text().strip()
            buttons.append([Button.inline(f"⏬ {ch_name}", data=f"kd_rd:{encode_url(ch_link)}")])
        
        buttons.append([Button.inline("« Kembali ke Pencarian", data="kd_back")])
        await event.edit(f"**Daftar Chapter:**\n{url}", buttons=buttons, link_preview=False)

    @callback(re.compile("kd_rd:(.*)"))
    async def kd_callback_read(event):
        if event.sender_id != ultroid_bot.uid:
            return await event.answer("Akses ditolak.", alert=True)
            
        raw_data = event.pattern_match.group(1).decode()
        url = decode_url(raw_data)
        
        await event.edit("`Mengunduh halaman komik...`", buttons=None)
        html = await fetch_page(url)
        if not html:
            return await event.respond("Gagal mengambil gambar.")

        soup = BeautifulSoup(html, 'html.parser')
        images = soup.find_all('img', class_='wp-manga-chapter-img')
        
        if not images:
            return await event.edit("Gambar tidak ditemukan.")

        await event.delete() # Clean up the message
        
        media = []
        count = 0
        for img in images:
            img_url = (img.get('src') or img.get('data-src') or "").strip()
            if img_url:
                # Bypass 403 using Google Proxy
                proxied_url = IMG_PROXY + img_url
                media.append(proxied_url)
                count += 1
            
            # Send in batches of 10 (Telegram Media Group limit)
            if len(media) == 10:
                await ultroid_bot.send_file(event.chat_id, media)
                media = []
        
        # Send remaining
        if media:
            await ultroid_bot.send_file(event.chat_id, media)
        
        await ultroid_bot.send_message(event.chat_id, f"✅ **Selesai!** Berhasil mengirim {count} halaman.")

    @callback("kd_back")
    async def kd_back(event):
        await event.edit("Gunakan kembali perintah `.kd <judul>` untuk mencari.")
