# Ultroid Addon - NHentai Inline (API Proxy Version)
# Author: itswill00
# Logic: Official API + Proxy (Most Stable)

import re
import httpx
from telethon import Button
from telethon.tl.types import InputWebDocument as wb
from . import InlinePlugin, in_pattern, asst, LOGS, async_searcher

# Register to the main Inline Menu
InlinePlugin.update({"NHᴇɴᴛᴀɪ": "nh"})

async def fetch_nh_api_latest():
    """Fetching latest galleries via Official API + Proxy"""
    try:
        # API All: Returns latest galleries
        url = "https://nhentai.net/api/galleries/all?page=1"
        proxy_url = f"https://api.codetabs.com/v1/proxy?quest={url}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                data = res.json()
                if "result" in data:
                    results = []
                    for gal in data["result"][:15]:
                        gid = gal["id"]
                        mid = gal["media_id"]
                        title = gal["title"].get("pretty") or gal["title"].get("english")
                        
                        # Thumb: https://t.nhentai.net/galleries/<media_id>/thumb.jpg (usually jpg)
                        thumb_url = f"https://t.nhentai.net/galleries/{mid}/thumb.jpg"
                        results.append({"id": gid, "title": title, "thumb": thumb_url})
                    return results
    except Exception as e:
        LOGS.error(f"NHentai API Latest Error: {e}")
    return []

async def fetch_nh_api_search(query):
    """Searching galleries via Official API + Proxy"""
    try:
        url = f"https://nhentai.net/api/galleries/search?query={query}&page=1"
        proxy_url = f"https://api.codetabs.com/v1/proxy?quest={url}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                data = res.json()
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
        LOGS.error(f"NHentai API Search Error: {e}")
    return []

@in_pattern("nh")
async def nhentai_inline_handler(event):
    query = event.text.split(" ", maxsplit=1)[1].strip() if " " in event.text else ""
    
    if not query:
        data = await fetch_nh_api_latest()
    else:
        data = await fetch_nh_api_search(query)

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
                title="API Unavailable",
                text="Gagal terhubung ke API NHentai via Proxy."
            )
        )

    await event.answer(results, cache_time=60)
