# Ultroid Addon - NHentai Inline
# Integration for NHentai Search & Latest Updates via Inline Mode
# Author: itswill00

import re
import httpx
from bs4 import BeautifulSoup
from telethon import Button
from telethon.tl.types import InputWebDocument as wb
from . import InlinePlugin, in_pattern, asst, LOGS, async_searcher

# Common Fetch Logic (Using Mirror to bypass Cloudflare)
async def fetch_nh_latest():
    try:
        # NHentai.xxx is a mirror that's often easier to scrape
        url = "https://nhentai.xxx/"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                # Mirror structure might be slightly different, let's adapt
                galleries = soup.find_all('div', class_='gallery')
                results = []
                for gal in galleries[:15]:
                    a_tag = gal.find('a')
                    gid = a_tag['href'].split('/')[-2]
                    title = gal.find('div', class_='caption').text.strip()
                    img = gal.find('img')
                    img_src = img.get('data-src') or img.get('src')
                    results.append({"id": gid, "title": title, "thumb": img_src})
                return results
    except Exception as e:
        LOGS.error(f"NHentai Inline Latest Error: {e}")
    return []

async def fetch_nh_search(query):
    try:
        # Search on mirror directly
        search_url = f"https://nhentai.xxx/search/?q={query}"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                galleries = soup.find_all('div', class_='gallery')
                results = []
                for gal in galleries[:15]:
                    a_tag = gal.find('a')
                    gid = a_tag['href'].split('/')[-2]
                    title = gal.find('div', class_='caption').text.strip()
                    img = gal.find('img')
                    img_src = img.get('data-src') or img.get('src')
                    results.append({"id": gid, "title": title, "thumb": img_src})
                return results
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
                await event.builder.article(
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
                await event.builder.article(
                    title=item['title'],
                    description=f"ID: {item['id']} | Search Result",
                    thumb=wb(item['thumb'], 0, "image/jpeg", []) if item['thumb'] else None,
                    text=f"**{item['title']}**\n`ID: {item['id']}`\n\n[Open on Web](https://nhentai.net/g/{item['id']}/)",
                    buttons=[Button.inline("📖 Read Now", data=f"nhp:1:{item['id']}")]
                )
            )

    if not results:
        results.append(
            await event.builder.article(
                title="No Results Found",
                text="Gagal menemukan manga di NHentai. (Mirror Timeout)"
            )
        )

    await event.answer(results, cache_time=300)

# Register to the main Inline Menu
InlinePlugin.update({"NHᴇɴᴛᴀɪ": "nh"})
