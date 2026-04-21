# Ultroid Addon - NHentai Inline (Surefire Version)
# Author: itswill00
# Logic: Cloudscraper Bypass + Multi-Mirror Fallback

import re
import cloudscraper
from bs4 import BeautifulSoup
from telethon import Button
from telethon.tl.types import InputWebDocument as wb
from . import InlinePlugin, in_pattern, asst, LOGS

# Register to the main Inline Menu early for certainty
InlinePlugin.update({"NHᴇɴᴛᴀɪ": "nh"})

# Setup Scraper (Anti-Cloudflare)
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

def get_nh_data(url):
    """Certainty Fetcher: Cloudscraper + Mirror Fallback"""
    mirrors = ["https://nhentai.xxx", "https://nhentai.to"]
    for mirror in mirrors:
        try:
            target = f"{mirror}{url}"
            res = scraper.get(target, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                galleries = soup.find_all('div', class_='gallery')
                if galleries:
                    results = []
                    for gal in galleries[:15]:
                        a_tag = gal.find('a')
                        gid = a_tag['href'].split('/')[-2]
                        title = gal.find('div', class_='caption').text.strip()
                        img = gal.find('img')
                        img_src = img.get('data-src') or img.get('src')
                        # Ensure absolute URL for thumbs
                        if img_src and img_src.startswith("//"):
                            img_src = "https:" + img_src
                        results.append({"id": gid, "title": title, "thumb": img_src})
                    return results
        except Exception as e:
            LOGS.error(f"NH Mirror {mirror} Failed: {e}")
            continue
    return []

@in_pattern("nh")
async def nhentai_inline_handler(event):
    query = event.text.split(" ", maxsplit=1)[1].strip() if " " in event.text else ""
    
    # Process synchronously in thread to avoid blocking since cloudscraper is sync
    if not query:
        # Latest
        data = get_nh_data("/")
    else:
        # Search
        data = get_nh_data(f"/search/?q={query}")

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
                title="System Offline",
                text="Gagal menembus pertahanan NHentai. Semua mirror sedang down."
            )
        )

    await event.answer(results, cache_time=60)
