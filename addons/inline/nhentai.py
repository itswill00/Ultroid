# Ultroid Addon - NHentai Inline
# Integration for NHentai Search & Latest Updates via Inline Mode
# Author: itswill00

import re
import httpx
from bs4 import BeautifulSoup
from telethon import Button
from telethon.tl.types import InputWebDocument as wb
from . import in_pattern, asst, LOGS, async_searcher

# Common Fetch Logic (Mirrored from hentai.py for independence)
async def fetch_nh_latest():
    try:
        url = "https://nhentai.net/"
        # Use direct fetch since we need it fast for inline
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                galleries = soup.find_all('div', class_='gallery')
                results = []
                for gal in galleries[:15]: # Get more for inline
                    gid = gal.find('a')['href'].split('/')[-2]
                    title = gal.find('div', class_='caption').text.strip()
                    # Thumb: https://t.nhentai.net/galleries/<media_id>/thumb.jpg
                    # We need media_id, let's get it from the img tag
                    img_src = gal.find('img')['data-src'] if gal.find('img').has_attr('data-src') else gal.find('img')['src']
                    results.append({"id": gid, "title": title, "thumb": img_src})
                return results
    except Exception as e:
        LOGS.error(f"NHentai Inline Latest Error: {e}")
    return []

async def fetch_nh_search(query):
    try:
        # Using DuckDuckGo search as a fallback if direct nhentai search is CF-protected
        search_url = f"https://duckduckgo.com/html/?q=site:nhentai.net+{query}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, 'html.parser')
            results = soup.find_all('a', class_='result__a', href=re.compile(r'nhentai\.net/g/\d+/'))
            
            final = []
            for res in results[:10]:
                m = re.search(r'/g/(\d+)/', res['href'])
                if m:
                    gid = m.group(1)
                    title = res.text.strip()
                    # We don't have thumbs from DDG easily, but we can guess or fetch API later
                    # For performance, we'll just use a placeholder or skip thumb for search
                    final.append({"id": gid, "title": title, "thumb": None})
            return final
    except Exception as e:
        LOGS.error(f"NHentai Inline Search Error: {e}")
    return []

@in_pattern("nh")
async def nhentai_inline_handler(event):
    query = event.text.split(" ", maxsplit=1)[1].strip() if " " in event.text else ""
    
    results = []
    if not query:
        # Show Latest
        data = await fetch_nh_latest()
        for item in data:
            results.append(
                event.builder.article(
                    title=item['title'],
                    description=f"ID: {item['id']} | Latest Update",
                    thumb=wb(item['thumb'], 0, "image/jpeg", []) if item['thumb'] else None,
                    text=f"**{item['title']}**\n`ID: {item['id']}`\n\n[Open on Web](https://nhentai.net/g/{item['id']}/)",
                    buttons=[Button.inline("📖 Read Now", data=f"nhp:1:{item['id']}")]
                )
            )
    else:
        # Search
        data = await fetch_nh_search(query)
        for item in data:
            results.append(
                event.builder.article(
                    title=item['title'],
                    description=f"ID: {item['id']} | Search Result",
                    text=f"**{item['title']}**\n`ID: {item['id']}`\n\n[Open on Web](https://nhentai.net/g/{item['id']}/)",
                    buttons=[Button.inline("📖 Read Now", data=f"nhp:1:{item['id']}")]
                )
            )

    if not results:
        results.append(
            event.builder.article(
                title="No Results Found",
                text="Gagal menemukan manga di NHentai."
            )
        )

    await event.answer(results, cache_time=300)
