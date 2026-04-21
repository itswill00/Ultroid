# Ultroid Addon - Hentai Nexus
# Multisource NSFW Plugin (Owner Only)
# Sources: NHentai, Hanime, Rule34

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

async def fetch_api(url, params=None):
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            res = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        LOGS.error(f"HentaiNexus API Error: {e}")
    return None

async def fetch_html(url):
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            # Using a simple proxy for potentially blocked sites
            proxy_url = f"https://api.codetabs.com/v1/proxy?quest={url}"
            res = await client.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                return res.text
    except Exception as e:
        LOGS.error(f"HentaiNexus HTML Error: {e}")
    return None

# --- COMMANDS ---

@ultroid_cmd(pattern="hentai( (.*)|$)", owner_only=True)
async def hentai_hub(event):
    query = event.pattern_match.group(1).strip()
    if not query:
        return await event.eor("`Gunakan: .hentai <kata kunci>`")

    buttons = [
        [
            Button.inline("📖 NHentai (Manga)", data=f"hnex:nh:{encode_url(query)}"),
            Button.inline("🎬 Hanime (Anime)", data=f"hnex:ha:{encode_url(query)}")
        ],
        [
            Button.inline("🎨 Rule34 (Art)", data=f"hnex:r34:{encode_url(query)}")
        ]
    ]
    await event.eor(f"**Hentai Nexus Hub**\n\nHasil untuk: `{query}`\nPilih sumber konten:", buttons=buttons)

@ultroid_cmd(pattern="nh( (.*)|$)", owner_only=True)
async def nh_direct(event):
    query = event.pattern_match.group(1).strip()
    if not query: return await event.eor("`Gunakan: .nh <kata kunci atau ID>`")
    # Redirect to callback logic for consistency
    await nh_search_logic(event, query)

@ultroid_cmd(pattern="ha( (.*)|$)", owner_only=True)
async def ha_direct(event):
    query = event.pattern_match.group(1).strip()
    if not query: return await event.eor("`Gunakan: .ha <kata kunci>`")
    await ha_search_logic(event, query)

@ultroid_cmd(pattern="r34( (.*)|$)", owner_only=True)
async def r34_direct(event):
    query = event.pattern_match.group(1).strip()
    if not query: return await event.eor("`Gunakan: .r34 <tags>`")
    await r34_search_logic(event, query)

# --- LOGIC HELPERS ---

async def fetch_nh_api(id):
    try:
        # Use a proxy to avoid Cloudflare on API too
        url = f"https://nhentai.net/api/gallery/{id}"
        async with httpx.AsyncClient(timeout=15) as client:
            proxy_url = f"https://api.codetabs.com/v1/proxy?quest={url}"
            res = await client.get(proxy_url)
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        LOGS.error(f"NHentai API Error: {e}")
    return None

async def nh_search_logic(event, query):
    xx = await event.eor("`Mencari di NHentai...`")
    if query.isdigit():
        data = await fetch_nh_api(query)
        if not data: return await xx.edit("`Gagal mengambil data. Mungkin ID salah atau diblokir.`")
        title = data['title']['pretty']
        return await xx.edit(f"**Found Gallery:**\n`{title}`", buttons=[Button.inline("📥 Read Now", data=f"hnex:nhrd:{query}")])
    
    # DuckDuckGo search for list
    search_url = f"https://duckduckgo.com/html/?q=site:nhentai.net+{query}"
    async with httpx.AsyncClient() as client:
        r = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, 'html.parser')
        results = soup.find_all('a', class_='result__a', href=re.compile(r'nhentai\.net/g/\d+/'))
        
        if not results: return await xx.edit("`Tidak ditemukan hasil di NHentai.`")
        
        buttons = []
        for res in results[:5]:
            m = re.search(r'/g/(\d+)/', res['href'])
            if m:
                id = m.group(1)
                buttons.append([Button.inline(f"📖 {res.text[:40]}", data=f"hnex:nhrd:{id}")])
        await xx.edit(f"**NHentai Results for:** `{query}`", buttons=buttons)

async def ha_search_logic(event, query):
    xx = await event.eor("`Mencari di Hanime...`")
    api_url = "https://search.htv-services.com/"
    data = {"search_text": query, "tags": [], "tags_mode": "AND", "brands": [], "blacklist": [], "order_by": "created_at_unix", "ordering": "desc", "page": 0}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(api_url, json=data)
            res_data = res.json()
            results = res_data.get('hits', [])
            if isinstance(results, str):
                try:
                    results = json.loads(results)
                except:
                    return await xx.edit("`Gagal memproses data dari Hanime.`")
            
            if not results or not isinstance(results, list):
                return await xx.edit("`Tidak ditemukan hasil di Hanime.`")
            
            buttons = []
            for hit in results[:5]:
                slug = hit.get('slug')
                title = hit.get('name', 'Unknown')
                if not slug: continue
                rating = hit.get('rating', 'N/A')
                buttons.append([Button.inline(f"🎬 {title[:30]} ({rating}⭐)", data=f"hnex:hard:{slug}")])
            
            if not buttons:
                return await xx.edit("`Tidak ditemukan hasil yang valid di Hanime.`")
            await xx.edit(f"**Hanime Results for:** `{query}`", buttons=buttons)
    except Exception as e:
        await xx.edit(f"**Error:** `{e}`")

async def r34_search_logic(event, query):
    xx = await event.eor("`Mencari di Rule34...`")
    api_url = "https://api.rule34.xxx/index.php"
    params = {"page": "dapi", "s": "post", "q": "index", "json": 1, "tags": query, "limit": 10}
    data = await fetch_api(api_url, params)
    if not data: return await xx.edit("`Tidak ditemukan hasil di Rule34.`")
    
    media = []
    for post in data:
        media.append(post['file_url'])
    
    await event.delete()
    await ultroid_bot.send_file(event.chat_id, media, caption=f"**Rule34 Results:** `{query}`")

# --- CALLBACKS ---

if asst:
    from . import callback

    @callback(re.compile("hnex:(.*)"))
    async def hnex_callback(event):
        if event.sender_id != ultroid_bot.uid:
            return await event.answer("Akses ditolak.", alert=True)
        
        data = event.pattern_match.group(1).decode().split(":")
        cmd = data[0]
        
        if cmd == "nh":
            query = decode_url(data[1])
            await nh_search_logic(event, query)
        elif cmd == "ha":
            query = decode_url(data[1])
            await ha_search_logic(event, query)
        elif cmd == "r34":
            query = decode_url(data[1])
            await r34_search_logic(event, query)
        elif cmd == "nhrd":
            id = data[1]
            await event.edit("`Fetching data from NHentai...`")
            data = await fetch_nh_api(id)
            if not data: return await event.edit("Gagal mengambil data gallery.")
            
            media_id = data['media_id']
            pages = data['images']['pages']
            
            await event.delete()
            images = []
            count = 0
            ext_map = {"j": "jpg", "p": "png", "g": "gif"}
            for i, page in enumerate(pages, 1):
                ext = ext_map.get(page['t'], "jpg")
                img_url = f"https://i.nhentai.net/galleries/{media_id}/{i}.{ext}"
                images.append(IMG_PROXY + img_url)
                count += 1
                if len(images) == 10:
                    await ultroid_bot.send_file(event.chat_id, images)
                    images = []
                if count >= 60: break # Increased limit slightly
            if images: await ultroid_bot.send_file(event.chat_id, images)
            await ultroid_bot.send_message(event.chat_id, f"✅ **Finished!** Sent {count} pages from NHentai (ID: {id}).")
        
        elif cmd == "hard":
            slug = data[1]
            await event.edit(f"**Direct Link:** https://hanime.tv/videos/hentai/{slug}", buttons=[Button.url("Watch on Web", f"https://hanime.tv/videos/hentai/{slug}")])
