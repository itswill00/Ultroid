# Ultroid Addon - NHentai Reader
# Focus: NHentai.net (Owner Only)
# Author: itswill00

import re
import base64
import json
import httpx
from bs4 import BeautifulSoup
from telethon import Button
from pyUltroid.fns.helper import run_async
from . import ultroid_cmd, udB, LOGS, asst, ultroid_bot, eor

# Google Focus Proxy to bypass direct image blocks
IMG_PROXY = "https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=2592000&url="

def encode_url(url):
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

def decode_url(data):
    if isinstance(data, bytes):
        data = data.decode()
    padding = '=' * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode()

async def fetch_nh_api(id):
    try:
        url = f"https://nhentai.net/api/gallery/{id}"
        async with httpx.AsyncClient(timeout=15) as client:
            proxy_url = f"https://api.codetabs.com/v1/proxy?quest={url}"
            res = await client.get(proxy_url)
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        LOGS.error(f"NHentai API Error: {e}")
    return None

async def fetch_latest_nh():
    try:
        url = "https://nhentai.net/"
        async with httpx.AsyncClient(timeout=15) as client:
            proxy_url = f"https://api.codetabs.com/v1/proxy?quest={url}"
            res = await client.get(proxy_url)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                galleries = soup.find_all('div', class_='gallery')
                results = []
                for gal in galleries[:5]: # Get latest 5
                    gid = gal.find('a')['href'].split('/')[-2]
                    title = gal.find('div', class_='caption').text.strip()
                    results.append((gid, title))
                return results
    except Exception as e:
        LOGS.error(f"NHentai Latest Error: {e}")
    return []

async def fetch_random_nh():
    try:
        # Use httpx to follow redirect and get the final URL
        url = "https://nhentai.net/random/"
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            # We need to hit nhentai directly or via a proxy that supports redirects
            # CodeTabs might not follow redirect correctly for this, let's try direct
            res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                # URL will be like https://nhentai.net/g/123456/
                gid = str(res.url).split('/')[-2]
                return gid
    except Exception as e:
        LOGS.error(f"NHentai Random Error: {e}")
    return None

# --- COMMANDS ---

@ultroid_cmd(pattern="nh( (.*)|$)", owner_only=True)
async def nh_search(event):
    query = event.pattern_match.group(1).strip()
    xx = await event.eor("`Processing...`")
    
    # Discovery: Latest
    if not query:
        latest = await fetch_latest_nh()
        if not latest:
            return await xx.edit("`Gagal mengambil data terbaru.`")
        msg = "**Latest NHentai Updates:**\n\n"
        buttons = []
        for i, (gid, title) in enumerate(latest, 1):
            msg += f"{i}. [{title}](https://nhentai.net/g/{gid}/)\n"
            buttons.append([Button.inline(f"📖 Read #{i}", data=f"nhp:1:{gid}")])
        return await xx.edit(msg, buttons=buttons, link_preview=False)

    # Discovery: Random
    if query.lower() == "random":
        gid = await fetch_random_nh()
        if not gid:
            return await xx.edit("`Gagal mendapatkan manga acak.`")
        data = await fetch_nh_api(gid)
        if not data:
            return await xx.edit("`Gagal memuat data manga acak.`")
        title = data['title']['pretty']
        msg = f"**🎲 Random Gacha Found:**\n`{title}`\n\n[Open on Web](https://nhentai.net/g/{gid}/)"
        return await xx.edit(msg, buttons=[Button.inline("📖 Read Now", data=f"nhp:1:{gid}")])

    # If query is ID
    if query.isdigit():
        data = await fetch_nh_api(query)
        if not data: return await xx.edit("`Gagal mengambil data. Mungkin ID salah atau diblokir.`")
        title = data['title']['pretty']
        msg = f"**Gallery Found:**\n`{title}`\n\n[Open on Web](https://nhentai.net/g/{query}/)"
        return await xx.edit(msg, buttons=[Button.inline("📖 Read Now", data=f"nhp:1:{query}")])

    # Search via DuckDuckGo
    search_url = f"https://duckduckgo.com/html/?q=site:nhentai.net+{query}"
    async with httpx.AsyncClient() as client:
        r = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('a', class_='result__a', href=re.compile(r'nhentai\.net/g/\d+/'))
        
        if not results: return await xx.edit("`Tidak ditemukan hasil.`")
        
        msg = f"**NHentai Results for:** `{query}`\n\n"
        buttons = []
        for i, res in enumerate(results[:5], 1):
            m = re.search(r'/g/(\d+)/', res['href'])
            if m:
                gid = m.group(1)
                title = res.text.strip()
                msg += f"{i}. [{title}](https://nhentai.net/g/{gid}/)\n"
                buttons.append([Button.inline(f"📖 Read #{i}", data=f"nhp:1:{gid}")])
        
        await xx.edit(msg, buttons=buttons, link_preview=False)

# --- CALLBACKS ---

if asst:
    from . import callback

    @callback(re.compile(r"nhp:(\d+):(\d+)"))
    async def nh_reader_callback(event):
        if event.sender_id != ultroid_bot.uid:
            return await event.answer("Akses ditolak.", alert=True)
        
        page = int(event.pattern_match.group(1))
        gid = event.pattern_match.group(2)
        
        await event.answer("Memuat halaman...", alert=False)
        
        data = await fetch_nh_api(gid)
        if not data:
            return await event.respond("Gagal mengambil data manga.")
            
        media_id = data['media_id']
        pages = data['images']['pages']
        total_pages = len(pages)
        
        if page < 1: page = 1
        if page > total_pages: page = total_pages
        
        # Determine extension
        ext_map = {"j": "jpg", "p": "png", "g": "gif"}
        current_page_data = pages[page-1]
        ext = ext_map.get(current_page_data['t'], "jpg")
        
        img_url = f"https://i.nhentai.net/galleries/{media_id}/{page}.{ext}"
        proxied_img = IMG_PROXY + img_url
        
        title = data['title']['pretty']
        caption = f"**{title}**\n`ID: {gid}`\n\n📖 **Halaman:** `{page}/{total_pages}`"
        
        buttons = []
        nav_row = []
        # Previous button
        if page > 1:
            nav_row.append(Button.inline("⬅️ Prev", data=f"nhp:{page-1}:{gid}"))
        else:
            nav_row.append(Button.inline("⏹ Start", data="none"))
            
        # Page Indicator
        nav_row.append(Button.inline(f"{page}/{total_pages}", data="none"))
        
        # Next button
        if page < total_pages:
            nav_row.append(Button.inline("Next ➡️", data=f"nhp:{page+1}:{gid}"))
        else:
            nav_row.append(Button.inline("⏹ End", data="none"))
            
        buttons.append(nav_row)
        buttons.append([Button.inline("❌ Close Reader", data="nh_close")])
        
        try:
            await event.edit(caption, file=proxied_img, buttons=buttons)
        except Exception:
            # If edit photo fails (maybe first time call), send new and delete old
            await event.delete()
            await ultroid_bot.send_file(event.chat_id, proxied_img, caption=caption, buttons=buttons)

    @callback("none")
    async def nh_none(event):
        await event.answer()

    @callback("nh_close")
    async def nh_close(event):
        await event.delete()
