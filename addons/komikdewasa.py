# Ultroid Addon - KomikDewasa (NSFW/Owner-Only)
# Website: https://komikdewasa.art/
# Author: itswill00

import re
from bs4 import BeautifulSoup
from pyUltroid.fns.helper import run_async
from . import ultroid_cmd, udB, LOGS, asst, ultroid_bot, eor

# Google Focus Proxy to bypass direct image blocks
IMG_PROXY = "https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=2592000&url="

async def fetch_page(url):
    import cloudscraper
    scraper = cloudscraper.create_scraper()
    try:
        # Nuclear headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://komikdewasa.art/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        }
        res = scraper.get(url, headers=headers, timeout=15)
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
    
    # Search logic via DuckDuckGo to bypass direct Cloudflare block
    import httpx
    search_url = f"https://duckduckgo.com/html/?q=site:komikdewasa.art+{query}"
    try:
        r = httpx.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('a', class_='result__a', href=re.compile(r'komikdewasa\.art/'))
        
        if not results:
            return await xx.edit("`Komik tidak ditemukan atau akses diblokir.`")

        output = "**Hasil Pencarian Komik:**\n\n"
        for i, res in enumerate(results[:5], 1):
            title = res.get_text()
            link = res['href']
            # Clean DuckDuckGo redirect link
            if "uddg=" in link:
                link = link.split("uddg=")[1].split("&")[0]
                from urllib.parse import unquote
                link = unquote(link)
            output += f"{i}. [{title}]({link})\n"
        
        output += "\n`Gunakan .kbread <link> untuk membaca.`"
        await xx.edit(output, link_preview=False)
    except Exception as e:
        await xx.edit(f"**Kesalahan:** `{e}`")

@ultroid_cmd(pattern="kbread( (.*)|$)", owner_only=True)
async def komik_dewasa_read(event):
    link = event.pattern_match.group(1).strip()
    if not link:
        return await event.eor("`Gunakan: .kbread <link komik>`")

    xx = await event.eor("`Menganalisis chapter...`")
    html = await fetch_page(link)
    if not html:
        return await xx.edit("`Gagal mengambil data. Cloudflare masih memblokir IP server.`")

    soup = BeautifulSoup(html, 'html.parser')
    
    # Madara/WP-Manga Theme chapter selector
    chapters = soup.find_all('li', class_='wp-manga-chapter')
    if not chapters:
        # Try finding images directly if it's already a chapter link
        images = soup.find_all('img', class_='wp-manga-chapter-img')
        if images:
            await xx.edit(f"`Menemukan {len(images)} halaman. Mengirim...`")
            media = []
            for img in images[:10]: # Limit 10 to avoid flood
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    img_url = img_url.strip()
                    # Use Google Proxy for images
                    proxied_url = IMG_PROXY + img_url
                    media.append(proxied_url)
            
            if media:
                await event.client.send_file(event.chat_id, media, caption=f"**Komik:** {link}")
                return await xx.delete()
        
        return await xx.edit("`Chapter tidak ditemukan.`")

    output = "**Daftar Chapter:**\n"
    for i, ch in enumerate(chapters[:10], 1):
        ch_link = ch.find('a')['href']
        ch_name = ch.find('a').get_text().strip()
        output += f"{i}. [{ch_name}]({ch_link})\n"

    await xx.edit(output, link_preview=False)
