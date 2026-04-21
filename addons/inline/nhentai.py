# Ultroid Addon - NHentai Inline (Dual-Layer Version)
# Author: itswill00
# Logic: API Proxy (AllOrigins) + Mirror Fallback

import re
import httpx
from bs4 import BeautifulSoup
from telethon import Button
from telethon.tl.types import InputWebDocument as wb
from . import InlinePlugin, in_pattern, asst, LOGS, async_searcher

# Register to the main Inline Menu
InlinePlugin.update({"NHᴇɴᴛᴀɪ": "nh"})

async def get_data_from_mirror(url_path):
    """Fallback logic: Scrape from mirror if API fails"""
    try:
        mirror = "https://nhentai.xxx"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(f"{mirror}{url_path}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                # nhentai.xxx uses 'gallery_item' class
                galleries = soup.find_all('div', class_='gallery_item')
                results = []
                for gal in galleries[:15]:
                    a_tag = gal.find('a')
                    if not a_tag: continue
                    gid = a_tag['href'].split('/')[-2]
                    caption = gal.find('div', class_='caption')
                    title = caption.text.strip() if caption else "No Title"
                    img = gal.find('img')
                    # Mirror uses data-src for lazy loading
                    img_src = img.get('data-src') or img.get('src')
                    if img_src and img_src.startswith("//"):
                        img_src = "https:" + img_src
                    results.append({"id": gid, "title": title, "thumb": img_src})
                return results
    except Exception as e:
        LOGS.error(f"NH Mirror Fallback Error: {e}")
    return []

async def fetch_nh_data(query=""):
    """Primary: API via AllOrigins Proxy | Secondary: Mirror Scrape"""
    try:
        if not query:
            url = "https://nhentai.net/api/galleries/all?page=1"
        else:
            url = f"https://nhentai.net/api/galleries/search?query={query}&page=1"
        
        # Using AllOrigins as primary proxy
        proxy_url = f"https://api.allorigins.win/raw?url={url}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                try:
                    data = res.json()
                except Exception:
                    # If not JSON, it might be a Cloudflare block from proxy
                    raise Exception("Proxy returned non-JSON response")
                
                if "result" in data:
                    results = []
                    for gal in data["result"][:15]:
                        gid = gal["id"]
                        mid = gal["media_id"]
                        title = gal["title"].get("pretty") or gal["title"].get("english")
                        thumb_url = f"https://t.nhentai.net/galleries/{mid}/thumb.jpg"
                        results.append({"id": gid, "title": title, "thumb": thumb_url})
                    return results
    except Exception as e:
        LOGS.error(f"NH API Proxy Error: {e}. Switching to mirror...")
    
    # If API Proxy fails, use Mirror Fallback
    path = "/" if not query else f"/search/?q={query}"
    return await get_data_from_mirror(path)

@in_pattern("nh")
async def nhentai_inline_handler(event):
    query = event.text.split(" ", maxsplit=1)[1].strip() if " " in event.text else ""
    data = await fetch_nh_data(query)

    results = []
    for item in data:
        results.append(
            await event.builder.article(
                title=item['title'],
                description=f"ID: {item['id']}",
                thumb=wb(item['thumb'], 0, "image/jpeg", []) if item['thumb'] else None,
                text=f"**{item['title']}**\n`ID: {item['id']}`\n\n[Open on Web](https://nhentai.net/g/{item['id']}/)",
                buttons=[Button.inline("📖 Read Now", data=f"nhp:1:{item['id']}")]
            )
        )

    if not results:
        results.append(
            await event.builder.article(
                title="System Down",
                text="Semua jalur (API & Mirror) gagal diakses. Coba lagi nanti."
            )
        )

    await event.answer(results, cache_time=60)
