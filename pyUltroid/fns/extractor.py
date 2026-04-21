# Ultroid Media Extraction Engine
# Powered by yt-dlp

import os
import re

from yt_dlp import YoutubeDL

from pyUltroid import LOGS
from pyUltroid.configs import Var
from pyUltroid.fns.helper import run_async

# Regex Patterns
TIKTOK_RE = re.compile(r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/\S+")
INSTAGRAM_RE = re.compile(r"https?://(?:www\.)?instagram\.com/(?:p|reels|reel|tv)/\S+")
TWITTER_RE = re.compile(r"https?://(?:www\.|mobile\.)?(?:twitter|x)\.com/\S+")
ADULT_RE = re.compile(
    r"https?://(?:www\.)?(?:"
    r"pornhub|xvideos|xhamster|xnxx|spankbang|eporner|redtube|youporn|tube8|xtube|"
    r"txxx|beeg|xhamsterlive|chaturbate|stripchat|bravotube|thumbzilla|faphouse|"
    r"rule34video|hqporner|daftsex|porntrex|vjav|javhd|missav|javguru|javcl|"
    r"japonx|netfapx|xozilla|pornhat|tubegalore|cliphunter|xmovies8"
    r")\.(?:com|net|org|tv|xxx|sex|tube|video|pro|cc|ws|mobi|co|sx)/\S+"
)
YOUTUBE_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com/(?:watch|shorts|live)\S*|youtu\.be/\S+)")

# TikTok Scraping Regex
UNIVERSAL_RE = re.compile(r'<script[^>]+\bid="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', re.S | re.I)
SIGI_RE = re.compile(r'<script[^>]+\bid="SIGI_STATE"[^>]*>(.*?)</script>', re.S | re.I)
NEXT_RE = re.compile(r'<script[^>]+\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S | re.I)

# Instagram Scraping Constants
IG_GRAPHQL_DOC_ID = "8845758582119845"
IG_GRAPHQL_ENDPOINT = "https://www.instagram.com/graphql/query/"
IG_SHORTCODE_RE = re.compile(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", re.I)

# Facebook Scraping Regex
FB_VIDEO_RE = re.compile(r"facebook\.com/(?:watch|reel|videos|posts|reels|share|story\.php|groups)|fb\.watch")
FB_HD_RE = re.compile(r'"progressive_url"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*,\s*"failure_reason"\s*:\s*[^,]+\s*,\s*"metadata"\s*:\s*\{\s*"quality"\s*:\s*"HD"\s*\}', re.S)
FB_SD_RE = re.compile(r'"progressive_url"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*,\s*"failure_reason"\s*:\s*[^,]+\s*,\s*"metadata"\s*:\s*\{\s*"quality"\s*:\s*"SD"\s*\}', re.S)

class MediaExtractor:
    def __init__(self, download_path="downloads/"):
        self.download_path = download_path
        self._extract_cache = {}  # Cache last extraction result to avoid double API calls
        self._http_session = None
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        try:
            import yt_dlp
            LOGS.info(f"Extractor | Engine: yt-dlp v{yt_dlp.version.__version__}")
        except Exception:
            LOGS.warning("Extractor | Could not determine yt-dlp version.")

        # --- One-time startup checks (cached as instance attributes) ---
        # Node detection: done ONCE at init, not on every get_opts() call.
        import shutil as _shutil
        _node_paths = [
            _shutil.which("node"),
            "/usr/bin/node",
            "/usr/local/bin/node",
            "/root/.nvm/versions/node/v24.15.0/bin/node",
        ]
        self._js_runtime = next((p for p in _node_paths if p and os.path.exists(p)), None)
        if self._js_runtime:
            LOGS.info(f"Extractor | JS Runtime: {self._js_runtime}")
        else:
            LOGS.warning(f"Extractor | No JS runtime found. Searched: {_node_paths}")

        # Cookie validation: done ONCE at init.
        self._cookie_file = None
        # aria2c detection
        self._aria2c = _shutil.which("aria2c")
        if self._aria2c:
            LOGS.info(f"Extractor | External Downloader: {self._aria2c}")

        if os.path.exists("cookies.txt"):
            try:
                with open("cookies.txt", "r") as _f:
                    _content = _f.read(500)
                if "# Netscape" in _content or "# http.cookiejar" in _content:
                    self._cookie_file = "cookies.txt"
                    LOGS.info("Extractor | cookies.txt loaded.")
                else:
                    LOGS.warning("Extractor | cookies.txt is NOT in Netscape format!")
            except Exception as _e:
                LOGS.warning(f"Extractor | Cookie integrity check failed: {_e}")
        else:
            LOGS.warning("Extractor | No cookies.txt found in root directory.")

        # PoToken / VisitorData — read once at init.
        _po = os.getenv("PO_TOKEN")
        _vd = os.getenv("VISITOR_DATA")
        self._yt_extractor_args: dict = {"player_client": ["tv_embedded", "web"]}
        if _po:
            self._yt_extractor_args["po_token"] = [f"web+{_po}"]
        if _vd:
            self._yt_extractor_args["visitor_data"] = [_vd]

    def get_opts(self, format_type="video", custom_opts=None, job_id=None, progress_callback=None):
        out_path = f"{self.download_path}{job_id}/" if job_id else self.download_path

        opts = {
            "outtmpl": f"{out_path}%(title).20s_%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "noplaylist": True,
            "age_limit": 21,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "concurrent_fragment_downloads": 1 if ADULT_RE.search(url) else 10,
            "buffersize": 1048576,  # 1 MB buffer for VPS throughput
            "extractor_args": {"youtube": self._yt_extractor_args},
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Dest": "document",
            },
        }

        if self._aria2c:
            # Disable aria2c for NSFW sites as they often block multi-connection downloads
            if not ADULT_RE.search(url):
                opts["external_downloader"] = "aria2c"
                opts["external_downloader_args"] = [
                    "--min-split-size=1M",
                    "--max-connection-per-server=16",
                    "--split=16",
                ]

        # Apply cached one-time results
        if self._js_runtime:
            opts["js_runtime"] = self._js_runtime
        if self._cookie_file:
            opts["cookiefile"] = self._cookie_file

        if format_type == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_type in ["1080", "720", "480"]:
            opts["format"] = f"bestvideo[height<={format_type}]+bestaudio/best[height<={format_type}]/best"
            opts["merge_output_format"] = "mp4"
        elif format_type == "extract":
            # Avoid any format selection for raw metadata extraction
            pass
        else:
            # Default to 'best' single-file format to avoid merge/ffmpeg issues on certain VPS
            opts["format"] = "best"
            opts["merge_output_format"] = "mp4"

        if custom_opts:
            opts.update(custom_opts)

        if progress_callback:
            opts["progress_hooks"] = [progress_callback]

        return opts

    @run_async
    def extract(self, url):
        """Extract metadata without downloading."""
        if url in self._extract_cache:
            return self._extract_cache[url]

        # TikTok Specific Scraping
        if TIKTOK_RE.search(url):
            try:
                res = self._tiktok_scrape(url)
                if not res or "error" in res:
                    res = self._tikwm_dl(url)

                if res and "error" not in res:
                    self._extract_cache[url] = res
                    return res
            except Exception as e:
                LOGS.warning(f"Extractor | TikTok scraping failed: {e}. Falling back to yt-dlp.")

        if "instagram.com" in url:
            try:
                # Prioritize local scraping (GraphQL & Embed)
                res = self._instagram_scrape(url)
                if res and "error" not in res:
                    self._extract_cache[url] = res
                    return res

                # Fallback to Sonzaix API for Instagram
                res = self._sonzaix_dl(url)
                if res and res.get("status"):
                    # Mock yt-dlp info structure for compatibility
                    results = res.get("result") or []
                    if not isinstance(results, list):
                        results = [results]

                    entries = []
                    for item in results:
                        u = item.get("url")
                        if u:
                            entries.append({
                                "url": u,
                                "ext": "mp4" if item.get("type") == "video" else "jpg",
                                "title": "Sonzaix_IG",
                                "id": "sonzaix",
                                "uploader": "Instagram",
                            })

                    if entries:
                        if len(entries) == 1:
                            info = entries[0]
                        else:
                            info = {
                                "entries": entries,
                                "title": "Sonzaix_IG_Carousel",
                                "uploader": "Instagram",
                                "uploader_url": url,
                            }

                        self._extract_cache[url] = info
                        return info
            except Exception as e:
                LOGS.warning(f"Extractor | Sonzaix API failed: {e}. Falling back to yt-dlp.")

        # Facebook Specific Scraping
        if FB_VIDEO_RE.search(url):
            try:
                res = self._facebook_scrape(url)
                if res and "error" not in res:
                    self._extract_cache[url] = res
                    return res
                # If our Genius Scraper and Cobalt API failed, yt-dlp will 100% fail.
                # Return the error cleanly to avoid terminal spam.
                if res and "error" in res:
                    return res
            except Exception as e:
                LOGS.warning(f"Extractor | Facebook scraping failed: {e}. Falling back to yt-dlp.")

        # YouTube Specific Fallback (Sonzai API)
        if YOUTUBE_RE.search(url):
            try:
                # Try Sonzai API if yt-dlp is known to be failing or as proactive fallback
                res = self._youtube_sonzai(url)
                if res and "error" not in res:
                    self._extract_cache[url] = res
                    return res
            except Exception as e:
                LOGS.warning(f"Extractor | YouTube Sonzai API failed: {e}. Falling back to yt-dlp.")

        opts = self.get_opts(format_type="extract")
        # Keep quiet=True to avoid yt-dlp spam in production logs.
        # Only log warnings/errors that are actionable.
        opts["ignoreerrors"] = False  # We handle errors ourselves via try/except

        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    LOGS.error(f"Extractor | Null info returned for {url}")
                    return {"error": "YouTube returned no metadata (Empty)."}
                self._extract_cache[url] = info
                return info
            except Exception as e:
                err_msg = str(e)
                # If specifically format error, try to list what WAS found
                if "Requested format is not available" in err_msg:
                    LOGS.error(f"Extractor | Format error for {url}. Attempting raw dump...")
                    try:
                        # Re-run with even looser opts to see what formats DO exist
                        info_raw = ydl.extract_info(url, download=False, process=False)
                        f_list = [f.get('format_id') for f in info_raw.get('formats', [])]
                        LOGS.info(f"Extractor | Available formats on VPS: {f_list}")
                        err_msg += f" | Available IDs: {f_list[:10]}"
                    except:
                        pass

                if "Sign in to confirm" in err_msg:
                    err_msg = "YouTube blocked this IP (Needs Cookies)."
                elif "403" in err_msg:
                    err_msg = "Access Forbidden (403)."
                elif "Video unavailable" in err_msg:
                    err_msg = "Video is private or unavailable."

                LOGS.warning(f"Extraction failed for {url}: {err_msg}")
                return {"error": err_msg}

    @staticmethod
    def _resolve_filename(ydl, info: dict) -> str:
        """Resolve actual file path after yt-dlp post-processing.

        `prepare_filename()` returns the name BEFORE post-processors run
        (e.g. FFmpeg can rename .webm → .mp4 after merge). This helper
        checks common extension variants so we always return an existing path.
        """
        raw = ydl.prepare_filename(info)
        if os.path.exists(raw):
            return raw

        # The file may have been renamed by a post-processor (e.g. FFmpeg merge)
        base, _ = os.path.splitext(raw)
        for ext in (".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".ogg", ".opus"):
            candidate = base + ext
            if os.path.exists(candidate):
                LOGS.debug(f"Extractor | Resolved post-processed file: {candidate}")
                return candidate

        # Fallback: return the raw name and let the caller handle missing file
        LOGS.warning(f"Extractor | Could not resolve file after post-processing: {raw}")
        return raw

    @run_async
    def download(self, url, format_type="video", job_id=None, progress_callback=None):
        """Download media with direct bypass for scraped URLs to avoid 403."""
        out_path_dir = os.path.join(self.download_path, job_id) if job_id else self.download_path
        os.makedirs(out_path_dir, exist_ok=True)

        # Step 1: Check Cache for Scraped Info
        info = self._extract_cache.get(url)

        # Step 2: If Scraped, Use Direct Downloader (Bypass yt-dlp)
        if info and info.get("extractor") in ["tiktok_scraper", "instagram_scraper", "facebook_scraper", "tikwm"]:
            LOGS.info(f"Extractor | Using Direct Downloader for {info['extractor']}")

            # Prepare Headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://www.tiktok.com/" if "tiktok" in url else "https://www.instagram.com/" if "instagram" in url else "https://www.facebook.com/"
            }
            if info.get("cookies"):
                headers["Cookie"] = info["cookies"]

            # Handle Album (Multiple Files)
            if info.get("type") == "album" or "entries" in info:
                files = []
                for idx, entry in enumerate(info["entries"]):
                    ext = entry.get("ext", "jpg")
                    filename = f"media_{idx}.{ext}"
                    path = os.path.join(out_path_dir, filename)
                    success = self._direct_download(entry["url"], path, headers)
                    if success: files.append(path)
                return files if files else None

            # Handle Single File
            video_url = info.get("url")
            if video_url:
                ext = info.get("ext", "mp4")
                filename = f"media_video.{ext}"
                path = os.path.join(out_path_dir, filename)
                success = self._direct_download(video_url, path, headers)
                return [path] if success else None

        # Step 3: Fallback to yt-dlp for other platforms (YouTube, etc.)
        opts = self.get_opts(url, format_type, job_id=job_id, progress_callback=progress_callback)
        with YoutubeDL(opts) as ydl:
            try:
                # If we have cached info from yt-dlp previously
                if not info or "error" in info:
                    info = ydl.extract_info(url, download=True)
                else:
                    info = ydl.extract_info(info["url"], download=True)

                if not info: return None
                if "entries" not in info:
                    return [self._resolve_filename(ydl, info)]

                files = []
                for entry in info.get("entries") or []:
                    if entry: files.append(self._resolve_filename(ydl, entry))
                return files or None
            except Exception as e:
                LOGS.error(f"Download failed for {url}: {e}")
                return None

    def _direct_download(self, url, path, headers):
        """Internal helper for direct download using aria2c or requests."""
        try:
            # Try aria2c first for speed
            if self._aria2c:
                import subprocess
                cmd = [self._aria2c, url, "-o", os.path.basename(path), "-d", os.path.dirname(path), "--quiet=true", "--allow-overwrite=true"]
                for k, v in headers.items():
                    cmd.extend(["--header", f"{k}: {v}"])
                subprocess.run(cmd, check=True, timeout=60)
                if os.path.exists(path): return True

            # Fallback to requests (synchronous but safe for direct download)
            import requests
            r = requests.get(url, headers=headers, stream=True, timeout=30)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception as e:
            LOGS.error(f"Direct Download Failed: {e}")
        return False

    def _sonzaix_dl(self, url):
        """Internal helper to fetch data from Sonzaix API."""
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            api_key = Var.SONZAIX_API_KEY
            key_param = f"&apikey={api_key}" if api_key else ""

            # Try /api/igdl first
            res = scraper.get(f"http://Api.sonzaix.indevs.in/api/igdl?url={url}{key_param}", timeout=15)
            if res.status_code == 200:
                return res.json()
            # Fallback to /api/v1/igdl
            res = scraper.get(f"http://Api.sonzaix.indevs.in/api/v1/igdl?url={url}{key_param}", timeout=15)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            LOGS.debug(f"Extractor | Sonzaix API error: {e}")
        return None

    def _instagram_scrape(self, url):
        """Scrape Instagram using GraphQL or Embed."""
        shortcode = IG_SHORTCODE_RE.search(url)
        if not shortcode:
            return {"error": "Invalid Instagram URL"}
        shortcode = shortcode.group(1)

        # Try GraphQL first
        res = self._instagram_gql(shortcode)
        if res and "error" not in res:
            return res

        # Fallback to Embed
        return self._instagram_embed(shortcode)

    def _instagram_gql(self, shortcode):
        """Fetch metadata via Instagram GraphQL API."""
        try:
            import base64
            import json
            import random
            import string

            import cloudscraper

            scraper = cloudscraper.create_scraper()

            def rand_alpha(n): return "".join(random.choice(string.ascii_letters) for _ in range(n))
            def rand_b64(n): return base64.urlsafe_b64encode(os.urandom(n)).decode().rstrip("=")

            csrf = rand_b64(24)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "x-ig-app-id": "936619743392459",
                "x-csrftoken": csrf,
                "content-type": "application/x-www-form-urlencoded",
                "cookie": f"csrftoken={csrf};",
                "Referer": f"https://www.instagram.com/p/{shortcode}/"
            }

            body = {
                "doc_id": IG_GRAPHQL_DOC_ID,
                "variables": json.dumps({"shortcode": shortcode, "fetch_tagged_user_count": None, "hoisted_comment_id": None, "hoisted_reply_id": None})
            }

            resp = scraper.post(IG_GRAPHQL_ENDPOINT, data=body, headers=headers, timeout=15)
            if resp.status_code != 200:
                return {"error": f"GraphQL HTTP {resp.status_code}"}

            data = resp.json()
            media = (data.get("data") or {}).get("xdt_shortcode_media") or (data.get("data") or {}).get("shortcode_media")
            if not media:
                return {"error": "Media not found in GraphQL response"}

            return self._parse_ig_media(media)
        except Exception as e:
            return {"error": str(e)}

    def _instagram_embed(self, shortcode):
        """Fetch metadata via Instagram Embed page."""
        try:
            import json

            import cloudscraper
            scraper = cloudscraper.create_scraper()
            url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
            resp = scraper.get(url, timeout=15)
            if resp.status_code != 200:
                return {"error": f"Embed HTTP {resp.status_code}"}

            html = resp.text
            # Extract JSON from ServerJS
            m = re.search(r'new ServerJS\(\)\);s\.handle\((\{.*?\})\);requireLazy', html, re.S)
            if m:
                # This is complex, but we try to find the shortcode_media inside contextJSON
                match = re.search(r'"contextJSON"\s*:\s*"((?:\\.|[^"\\])*)"', m.group(1), re.S)
                if match:
                    ctx_raw = json.loads('"' + match.group(1) + '"')
                    ctx_data = json.loads(ctx_raw)
                    media = (ctx_data.get("gql_data") or {}).get("shortcode_media")
                    if media:
                        return self._parse_ig_media(media)

            return {"error": "Could not find metadata in Embed"}
        except Exception as e:
            return {"error": str(e)}

    def _parse_ig_media(self, media):
        """Unified parser for Instagram media objects."""
        typename = media.get("__typename")
        owner = media.get("owner") or {}

        info = {
            "title": (media.get("edge_media_to_caption", {}).get("edges") or [{}])[0].get("node", {}).get("text") or "Instagram Media",
            "uploader": owner.get("full_name") or owner.get("username") or "Instagram User",
            "uploader_url": f"https://instagram.com/{owner.get('username')}" if owner.get("username") else None,
            "id": media.get("shortcode"),
            "extractor": "instagram_scraper"
        }

        if typename in ("GraphSidecar", "XDTGraphSidecar"):
            info["entries"] = []
            info["type"] = "album"
            for edge in media.get("edge_sidecar_to_children", {}).get("edges") or []:
                node = edge.get("node")
                if node:
                    item = {
                        "url": node.get("video_url") or node.get("display_url"),
                        "ext": "mp4" if node.get("is_video") else "jpg",
                        "title": info["title"]
                    }
                    info["entries"].append(item)
        else:
            info["url"] = media.get("video_url") or media.get("display_url")
            info["ext"] = "mp4" if media.get("is_video") else "jpg"

        return info

    def _facebook_scrape(self, url):
        """God Mode Zero-Cookie Facebook scraper with Nuclear Hijacking strategies."""
        LOGS.info(f"Extractor | Facebook NUCLEAR Mode: {url}")
        try:
            from urllib.parse import quote, unquote

            import requests
            # Use requests.Session for more control over TLS and headers
            scraper = requests.Session()

            # Match debug script UA
            DESKTOP_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            scraper.headers.update({"User-Agent": DESKTOP_UA})

            # --- PHASE -1: Cookie Integration ---
            if hasattr(self, "_cookie_file") and self._cookie_file:
                try:
                    from http.cookiejar import MozillaCookieJar
                    cj = MozillaCookieJar(self._cookie_file)
                    cj.load(ignore_discard=True, ignore_expires=True)
                    scraper.cookies.update(cj)
                    # Session warmup
                    scraper.get("https://www.facebook.com/", timeout=7)
                    LOGS.info(f"Extractor | Facebook Cookies Integrated ({len(scraper.cookies)} items).")
                except Exception as e:
                    LOGS.error(f"Extractor | Cookie Integration Error: {e}")

            def unescape_fb(text):
                try:
                    return text.replace(r"\/", "/").encode().decode('unicode-escape', errors='ignore')
                except: return text.replace(r"\/", "/")

            # --- CUNNING STRATEGY 1: Nuclear Regex Vacuum ---
            def nuclear_vacuum(text):
                text = unescape_fb(text)
                # 1. Look for HD Video (The Gold Standard)
                for p in [
                    r'"playable_url_quality_hd"\s*:\s*"(https?://[^"]+)"',
                    r'"hd_src"\s*:\s*"(https?://[^"]+)"',
                    r'hd_src_no_ratelimit:"(https?://[^"]+)"',
                    r'"browser_native_hd_url"\s*:\s*"(https?://[^"]+)"'
                ]:
                    m = re.search(p, text)
                    if m: return {"url": m.group(1), "ext": "mp4", "extractor": "fb_nuclear_hd"}
                # 2. Look for SD/Progressive Video
                for p in [
                    r'"playable_url"\s*:\s*"(https?://[^"]+)"',
                    r'"sd_src"\s*:\s*"(https?://[^"]+)"',
                    r'"progressive_url"\s*:\s*"(https?://[^"]+)"',
                    r'video_url":"(https?://[^"]+)"',
                    r'"browser_native_sd_url"\s*:\s*"(https?://[^"]+)"'
                ]:
                    m = re.search(p, text)
                    if m: return {"url": m.group(1), "ext": "mp4", "extractor": "fb_nuclear_sd"}
                # 3. Look for High-Res Photos
                for p in [r'"large_image_url"\s*:\s*"(https?://[^"]+)"', r'"scaled_image_url"\s*:\s*"(https?://[^"]+)"', r'og:image"\s+content="(https?://[^"]+)"']:
                    m = re.search(p, text)
                    if m: return {"url": m.group(1), "ext": "jpg", "extractor": "fb_nuclear_img"}
                return None

            # --- CUNNING STRATEGY 2: Publer.io Hijack (The Professional Bypass) ---
            LOGS.info("Extractor | Cunning Strategy 2: Publer Hijack...")
            try:
                p_api = "https://publer.io/api/v1/tools/media-downloader"
                p_resp = scraper.post(p_api, json={"url": url, "link": url}, timeout=12)
                if p_resp.status_code == 200:
                    p_payload = p_resp.json().get("payload", [])
                    for item in p_payload:
                        path = item.get("path")
                        if path:
                            LOGS.info("Extractor | Cunning Strategy 2: SUCCESS!")
                            return {"url": path, "title": "Facebook Media (Publer)", "ext": "mp4" if ".mp4" in path else "jpg", "extractor": "fb_publer"}
            except Exception as e: LOGS.debug(f"Publer failed: {e}")

            # --- CUNNING STRATEGY 3: SnapSave Hijack (The Liar Bypass) ---
            LOGS.info("Extractor | Cunning Strategy 3: SnapSave Hijack...")
            try:
                ss_api = "https://snapsave.app/action.php?lang=en"
                ss_resp = scraper.post(ss_api, data={"url": url}, headers={"Referer": "https://snapsave.app/"}, timeout=10)
                if ss_resp.status_code == 200:
                    res = nuclear_vacuum(ss_resp.text)
                    if res: return res
            except: pass

            # --- CUNNING STRATEGY 4: FDown.net Hijack (The Classic) ---
            LOGS.info("Extractor | Cunning Strategy 4: FDown Hijack...")
            try:
                fd_resp = scraper.post("https://fdown.net/download.php", data={"URL": url}, timeout=10)
                if fd_resp.status_code == 200:
                    # Look for HD/SD links in HTML
                    m_hd = re.search(r'id="hdlink"\s+href="([^"]+)"', fd_resp.text)
                    if m_hd: return {"url": unescape_fb(m_hd.group(1)), "ext": "mp4", "extractor": "fb_fdown_hd"}
                    m_sd = re.search(r'id="sdlink"\s+href="([^"]+)"', fd_resp.text)
                    if m_sd: return {"url": unescape_fb(m_sd.group(1)), "ext": "mp4", "extractor": "fb_fdown_sd"}
            except: pass

            # --- PHASE 1: Direct ID Extraction ---
            content_id = None
            patterns = [
                r"share/[pv]/([A-Za-z0-9]+)",
                r"posts/([0-9]+)",
                r"videos/([0-9]+)",
                r"reel/([0-9]+)",
                r"fbid=([0-9]+)",
                r"story_fbid=([0-9]+)",
                r"post_id=([0-9]+)",
                r"/([0-9]{10,})"
            ]
            for p in patterns:
                m = re.search(p, url)
                if m:
                    content_id = m.group(1)
                    break

            # --- PHASE 2: CUNNING STRATEGY 5 (Prioritized) ---
            if content_id:
                LOGS.info(f"Extractor | Cunning Strategy 5: Deep Crawl ({content_id})")
                targets = [
                    f"https://mbasic.facebook.com/{content_id}",
                    f"https://www.facebook.com/plugins/post.php?href={quote(url)}",
                    f"https://www.facebook.com/plugins/video.php?v={content_id}"
                ]

                # Standard Desktop UA that matches debug script
                DESKTOP_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

                for target in targets:
                    try:
                        resp = scraper.get(target, headers={"User-Agent": DESKTOP_UA}, timeout=10)
                        html = resp.text
                        res = nuclear_vacuum(html)
                        if res: return res

                        m_vid = re.search(r'href="(/video_redirect/[^"]+)"', html)
                        if m_vid:
                            vid_url = unquote(unescape_fb(m_vid.group(1).replace("&amp;", "&")))
                            if "/video_redirect/?src=" in vid_url:
                                vid_url = vid_url.split("src=")[1].split("&")[0]
                                return {"url": unquote(vid_url), "ext": "mp4", "extractor": "fb_mbasic_vid"}

                        if "mbasic" in target:
                            imgs = re.findall(r'src="(https://scontent\.[^"]+)"', html)
                            if imgs:
                                for img in imgs:
                                    if "stp=dst-jpg" in img or "/v/" in img:
                                        return {"url": unescape_fb(img), "ext": "jpg", "extractor": "fb_mbasic_img"}
                                return {"url": unescape_fb(imgs[0]), "ext": "jpg", "extractor": "fb_mbasic_img"}
                    except: continue

            # --- PHASE 3: Fallback URL Resolution ---
            LOGS.info(f"Extractor | Resolving Facebook URL (Fallback): {url}")
            resolved_url = url
            try:
                r = scraper.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, allow_redirects=True, timeout=10)
                resolved_url = r.url
            except: pass

            # --- PHASE 3: Wild Card Fallback ---
            return self._facebook_public_api(resolved_url)

        except Exception as e:
            LOGS.error(f"Extractor | FB God Mode Crash: {e}")
            return self._facebook_public_api(url)

    def _facebook_public_api(self, url):
        """The 'Wild Card' Multi-API Aggregator (featuring Cobalt)."""
        LOGS.info("Extractor | Activating Wild Card: Cobalt API...")
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()

            # --- Weapon 1: Cobalt API (The Ultimate Bypass) ---
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            # Public Cobalt instances (can be rotated if one fails)
            cobalt_instances = [
                "https://cobalt.now.sh/api/json",
                "https://api.cobalt.tools/api/json",
                "https://co.wuk.sh/api/json",
                "https://cobalt.api.unblocked.top/api/json",
                "https://cobalt-api.kwiateusz.xyz/api/json",
                "https://api.cobalt.black/api/json",
                "https://cobalt.night-street.com/api/json"
            ]

            for instance in cobalt_instances:
                try:
                    resp = scraper.post(instance, json={"url": url}, headers=headers, timeout=15)
                    if resp.status_code == 200:
                        res = resp.json()
                        status = res.get("status")

                        if status in ["stream", "redirect"]:
                            LOGS.info("Extractor | Cobalt API Success: Single Media")
                            return {
                                "url": res.get("url"),
                                "title": "Facebook Media (Cobalt Bypass)",
                                "ext": "mp4",
                                "uploader": "Facebook",
                                "extractor": "cobalt_api"
                            }
                        elif status == "picker":
                            # Carousel / Album handler
                            LOGS.info("Extractor | Cobalt API Success: Album/Carousel")
                            entries = []
                            for item in res.get("picker", []):
                                entries.append({
                                    "url": item.get("url"),
                                    "ext": "jpg" if item.get("type") == "photo" else "mp4",
                                    "title": "Facebook Album"
                                })
                            if entries:
                                return {
                                    "entries": entries,
                                    "type": "album",
                                    "title": "Facebook Album (Cobalt Bypass)",
                                    "extractor": "cobalt_api"
                                }
                except Exception as e:
                    LOGS.debug(f"Extractor | Cobalt Instance {instance} failed: {e}")

            # --- Weapon 2: Sonzaix (Legacy Fallback) ---
            LOGS.info("Extractor | Cobalt failed. Falling back to Sonzaix...")
            api_url = f"https://api.sonzaix.indevs.in/facebook/video?url={url}"
            resp = scraper.get(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                video_url = data.get("url") or data.get("hd") or data.get("sd")
                if video_url:
                    return {
                        "url": video_url,
                        "title": data.get("title", "Facebook Video"),
                        "ext": "mp4",
                        "uploader": "Facebook",
                        "extractor": "facebook_api"
                    }
        except Exception as e:
            LOGS.error(f"Extractor | Wild Card Aggregator failed: {e}")

        # If we reach here, it's 99% a private group post.
        return {"error": "Access Denied. This post is likely private or restricted. A cookies.txt file is mandatory for this URL."}

    def _youtube_sonzai(self, url):
        """YouTube API fallback using Sonzai/Indevs API."""
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            # This API endpoint is often used as a bypass for blocked VPS IPs
            api_url = f"https://api.sonzaix.indevs.in/youtube/video?url={url}"
            resp = scraper.get(api_url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                links = data.get("download_link", {})
                if not links:
                    return {"error": "No download links found in Sonzai API"}

                # Pick best available resolution (e.g. 720p)
                best_label = sorted(links.keys(), key=lambda x: int(re.search(r"\d+", x).group(0) if re.search(r"\d+", x) else 0), reverse=True)[0]
                video_url = links[best_label]

                return {
                    "url": video_url,
                    "title": data.get("filename", "YouTube Video").split(".mp4")[0],
                    "ext": "mp4",
                    "uploader": "YouTube",
                    "extractor": "sonzai_youtube"
                }
        except Exception as e:
            LOGS.debug(f"Extractor | YouTube Sonzai API error: {e}")
        return {"error": "YouTube API fallback failed"}

    def _tiktok_scrape(self, url):
        """Robust TikTok scraping with detailed logging."""
        LOGS.info(f"Extractor | TikTok Scraping started for: {url}")
        try:
            import json

            import cloudscraper
            scraper = cloudscraper.create_scraper()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.tiktok.com/",
                "Accept-Language": "en-US,en;q=0.9",
            }

            # Step 1: Resolve URL
            try:
                resp = scraper.get(url, headers=headers, allow_redirects=True, timeout=15)
                # Capture cookies for download phase
                session_cookies = "; ".join([f"{c.name}={c.value}" for c in scraper.cookies])
            except Exception as e:
                LOGS.error(f"Extractor | TikTok resolve failed: {e}")
                return {"error": f"Resolve failed: {e}"}

            resolved_url = resp.url
            html_text = resp.text
            LOGS.info(f"Extractor | Resolved URL: {resolved_url} (Status: {resp.status_code})")

            if resp.status_code == 403:
                LOGS.warning("Extractor | TikTok returned 403 Forbidden on initial request.")

            aweme_match = re.search(r"/(?:video|photo|v|reels)/(\d+)", resolved_url)
            aweme_id = aweme_match.group(1) if aweme_match else None

            if not aweme_id:
                aweme_match = re.search(r'video(?:Id|ID|id)"\s*:\s*"(\d+)"', html_text)
                aweme_id = aweme_match.group(1) if aweme_match else None

            # Step 2: Define targets
            targets = [resolved_url]
            if aweme_id:
                LOGS.info(f"Extractor | Found Aweme ID: {aweme_id}")
                targets.append(f"https://www.tiktok.com/embed/v3/{aweme_id}")
                targets.append(f"https://www.tiktok.com/@_/video/{aweme_id}")

            data = None
            item = None

            for target in targets:
                LOGS.info(f"Extractor | Trying target: {target}")
                if target != resolved_url:
                    try:
                        resp = scraper.get(target, headers=headers, timeout=15)
                        html_text = resp.text
                        # Update cookies if target changed
                        session_cookies = "; ".join([f"{c.name}={c.value}" for c in scraper.cookies])
                    except Exception as e:
                        LOGS.warning(f"Extractor | Target {target} failed: {e}")
                        continue

                if "/login" in resp.url or "verify-center" in html_text:
                    LOGS.warning(f"Extractor | Target {target} blocked by Captcha/Login.")
                    continue

                for regex in [UNIVERSAL_RE, SIGI_RE, NEXT_RE]:
                    match = regex.search(html_text)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            def find_item(obj):
                                if isinstance(obj, dict):
                                    if "itemStruct" in obj: return obj["itemStruct"]
                                    if "itemInfo" in obj: return obj["itemInfo"].get("itemStruct") or obj["itemInfo"]
                                    for v in obj.values():
                                        res = find_item(v)
                                        if res: return res
                                elif isinstance(obj, list):
                                    for i in obj:
                                        res = find_item(i)
                                        if res: return res
                                return None

                            item = find_item(data)
                            if item:
                                LOGS.info(f"Extractor | Successfully parsed itemStruct from {target}")
                                break
                        except Exception:
                            continue
                if item: break

            if not item:
                LOGS.warning("Extractor | Could not find itemStruct in HTML metadata.")
                return {"error": "ItemStruct not found"}

            info = {
                "title": item.get("desc") or item.get("description") or "TikTok Media",
                "uploader": item.get("author", {}).get("nickname") or item.get("author", {}).get("uniqueId") or "TikTok User",
                "id": aweme_id or item.get("id"),
                "extractor": "tiktok_scraper",
                "cookies": session_cookies # Store cookies for download
            }

            image_post = item.get("imagePost") or item.get("image_post")
            if image_post and image_post.get("images"):
                info["entries"] = []
                info["type"] = "album"
                for img in image_post["images"]:
                    u = (img.get("displayImage") or img.get("imageURL") or img.get("video") or {}).get("urlList", [None])[0]
                    if u:
                        info["entries"].append({"url": u, "ext": "jpg", "title": info["title"]})
                LOGS.info(f"Extractor | Detected Slideshow with {len(info['entries'])} images.")
            else:
                video = item.get("video") or {}
                video_url = video.get("playAddr") or video.get("downloadAddr") or video.get("play_addr", {}).get("url_list", [None])[0]
                if not video_url:
                    video_url = item.get("video_url")

                info["url"] = video_url
                info["ext"] = "mp4"
                LOGS.info(f"Extractor | Detected Video: {info['url'][:50]}...")

            if not info.get("url") and not info.get("entries"):
                return {"error": "Media URLs missing"}

            return info
        except Exception as e:
            LOGS.error(f"Extractor | TikTok scraping crash: {e}")
            return {"error": str(e)}

    def _tikwm_dl(self, url):
        """Enhanced TikWM fallback with better logging and error handling."""
        LOGS.info(f"Extractor | Trying TikWM API for: {url}")
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            # TikWM sometimes needs specific headers or it returns 403
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Origin": "https://www.tikwm.com",
                "Referer": "https://www.tikwm.com/",
            }
            res = scraper.post("https://www.tikwm.com/api/", data={"url": url}, headers=headers, timeout=15)

            if res.status_code != 200:
                LOGS.warning(f"Extractor | TikWM API returned HTTP {res.status_code}")
                return {"error": f"TikWM HTTP {res.status_code}"}

            data = res.json()
            if data.get("code") == 0:
                item = data.get("data")
                info = {
                    "title": item.get("title") or item.get("desc") or "TikTok Video",
                    "uploader": item.get("author", {}).get("nickname") or "TikTok User",
                    "id": item.get("id"),
                    "extractor": "tikwm"
                }

                images = item.get("images")
                if images and isinstance(images, list):
                    info["entries"] = [{"url": u, "ext": "jpg"} for u in images]
                    info["type"] = "album"
                    LOGS.info(f"Extractor | TikWM: Detected Slideshow ({len(images)} images)")
                else:
                    info["url"] = item.get("play") or item.get("wmplay") or item.get("hdplay")
                    info["ext"] = "mp4"
                    LOGS.info("Extractor | TikWM: Detected Video URL")
                return info
            else:
                msg = data.get("msg") or "Unknown TikWM error"
                LOGS.warning(f"Extractor | TikWM API error: {msg}")
                return {"error": msg}
        except Exception as e:
            LOGS.error(f"Extractor | TikWM API crash: {e}")
            return {"error": str(e)}

# Global Instance
extractor = MediaExtractor()
