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
ADULT_RE = re.compile(r"https?://(?:www\.)?(?:pornhub\.com|xvideos\.com|xhamster\.com|xnxx\.com|spankbang\.com|eporner\.com)/\S+")
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
FB_VIDEO_RE = re.compile(r"facebook\.com/(?:watch|reel|videos|posts|reels)|fb\.watch")
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
                if "# Netscape" not in _content:
                    LOGS.warning("Extractor | cookies.txt is NOT in Netscape format!")
                elif "\t" not in _content and "  " in _content:
                    LOGS.error("Extractor | cookies.txt has SPACE-indentation instead of TABS (paste error).")
                else:
                    self._cookie_file = "cookies.txt"
                    LOGS.info("Extractor | cookies.txt loaded.")
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
            "concurrent_fragment_downloads": 10,
            "buffersize": 1048576,  # 1 MB buffer for VPS throughput
            "extractor_args": {"youtube": self._yt_extractor_args},
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        if self._aria2c:
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
            opts["format"] = f"bestvideo[height<={format_type}]+bestaudio/best[height<={format_type}]"
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
                
                if res and not "error" in res:
                    self._extract_cache[url] = res
                    return res
            except Exception as e:
                LOGS.warning(f"Extractor | TikTok scraping failed: {e}. Falling back to yt-dlp.")

        if "instagram.com" in url:
            try:
                # Prioritize local scraping (GraphQL & Embed)
                res = self._instagram_scrape(url)
                if res and not "error" in res:
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
                if res and not "error" in res:
                    self._extract_cache[url] = res
                    return res
            except Exception as e:
                LOGS.warning(f"Extractor | Facebook scraping failed: {e}. Falling back to yt-dlp.")

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
        """Download media and return the file path(s)."""
        if job_id:
            os.makedirs(os.path.join(self.download_path, job_id), exist_ok=True)

        # Use cached info if available to avoid double extraction
        info = self._extract_cache.get(url)

        opts = self.get_opts(format_type, job_id=job_id, progress_callback=progress_callback)
        with YoutubeDL(opts) as ydl:
            try:
                if not info:
                    info = ydl.extract_info(url, download=True)
                else:
                    # If we have cached info (e.g. from Sonzaix), download it
                    # yt-dlp can download from a processed info dict via process_ie_data
                    if "entries" in info:
                        # For carousel/multi-file
                        files = []
                        for entry in info["entries"]:
                            # Force download of the direct URL
                            e_info = ydl.extract_info(entry["url"], download=True)
                            if e_info:
                                files.append(self._resolve_filename(ydl, e_info))
                        return files or None
                    else:
                        # For single file
                        info = ydl.extract_info(info["url"], download=True)

                if not info:
                    return None

                # Handle single file
                if "entries" not in info:
                    return [self._resolve_filename(ydl, info)]

                # Handle multi-file (TikTok slides, IG Carousel, etc.)
                files = []
                for entry in info.get("entries") or []:
                    if entry:
                        files.append(self._resolve_filename(ydl, entry))
                return files or None
            except Exception as e:
                LOGS.error(f"Download failed for {url}: {e}")
                return None

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
        if res and not "error" in res:
            return res
        
        # Fallback to Embed
        return self._instagram_embed(shortcode)

    def _instagram_gql(self, shortcode):
        """Fetch metadata via Instagram GraphQL API."""
        try:
            import cloudscraper
            import json
            import random
            import string
            import base64

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
            import cloudscraper
            import json
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
        """Scrape Facebook HTML for HD/SD video URLs."""
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            # Follow redirects (especially for fb.watch)
            resp = scraper.get(url, headers=headers, allow_redirects=True, timeout=15)
            html = resp.text
            
            def unescape_fb(text):
                return text.replace(r"\/", "/").encode().decode('unicode-escape')

            hd_match = FB_HD_RE.search(html)
            sd_match = FB_SD_RE.search(html)
            
            video_url = None
            if hd_match:
                video_url = unescape_fb(hd_match.group(1))
            elif sd_match:
                video_url = unescape_fb(sd_match.group(1))
                
            if not video_url:
                return {"error": "Facebook video URL not found in HTML"}
            
            # Extract title if possible
            title = "Facebook Video"
            title_match = re.search(r'<title id="pageTitle">(.*?)</title>', html)
            if title_match:
                title = title_match.group(1)

            return {
                "url": video_url,
                "title": title,
                "ext": "mp4",
                "uploader": "Facebook",
                "extractor": "facebook_scraper"
            }
        except Exception as e:
            return {"error": str(e)}

    def _tiktok_scrape(self, url):
        """Robust TikTok scraping using multi-target strategy."""
        try:
            import cloudscraper
            import json
            scraper = cloudscraper.create_scraper()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.tiktok.com/",
            }
            
            # Step 1: Resolve URL and extract aweme_id
            resp = scraper.get(url, headers=headers, allow_redirects=True, timeout=15)
            resolved_url = resp.url
            aweme_match = re.search(r"/(?:video|photo|v)/(\d+)", resolved_url)
            aweme_id = aweme_match.group(1) if aweme_match else None
            
            if not aweme_id:
                # Try to find ID in HTML if not in URL
                aweme_match = re.search(r'video(?:Id|ID|id)"\s*:\s*"(\d+)"', resp.text)
                aweme_id = aweme_match.group(1) if aweme_match else None

            # Step 2: Define targets to scrape
            targets = [resolved_url]
            if aweme_id:
                targets.append(f"https://www.tiktok.com/embed/v3/{aweme_id}")
                targets.append(f"https://www.tiktok.com/@_/video/{aweme_id}")

            data = None
            item = None
            
            # Step 3: Try each target
            for target in targets:
                if target != resolved_url:
                    resp = scraper.get(target, headers=headers, timeout=15)
                
                html_text = resp.text
                if "/login" in resp.url or "verify-center" in html_text:
                    continue

                for regex in [UNIVERSAL_RE, SIGI_RE, NEXT_RE]:
                    match = regex.search(html_text)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            # Deep search for itemStruct/itemInfo
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
                            if item: break
                        except:
                            continue
                if item: break

            if not item:
                return {"error": "Could not extract TikTok itemStruct from any target."}

            # Step 4: Map to internal info dict
            info = {
                "title": item.get("desc") or item.get("description") or "TikTok Media",
                "uploader": item.get("author", {}).get("nickname") or item.get("author", {}).get("uniqueId") or "TikTok User",
                "id": aweme_id or item.get("id"),
                "extractor": "tiktok_scraper"
            }

            # Handle Slideshow (Images)
            image_post = item.get("imagePost") or item.get("image_post")
            if image_post and image_post.get("images"):
                info["entries"] = []
                info["type"] = "album"
                for img in image_post["images"]:
                    # Try various URL locations
                    u = (img.get("displayImage") or img.get("imageURL") or img.get("video") or {}).get("urlList", [None])[0]
                    if u:
                        info["entries"].append({"url": u, "ext": "jpg", "title": info["title"]})
            else:
                # Handle Video
                video = item.get("video") or {}
                video_url = video.get("playAddr") or video.get("downloadAddr") or video.get("play_addr", {}).get("url_list", [None])[0]
                if not video_url:
                    # Last ditch effort for video URL
                    video_url = item.get("video_url")
                
                info["url"] = video_url
                info["ext"] = "mp4"

            if not info.get("url") and not info.get("entries"):
                return {"error": "Media URLs not found in TikTok data."}

            return info
        except Exception as e:
            return {"error": str(e)}

    def _tikwm_dl(self, url):
        """Fallback TikTok API using tikwm.com."""
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            res = scraper.post("https://www.tikwm.com/api/", data={"url": url}, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if data.get("code") == 0:
                    item = data.get("data")
                    info = {
                        "title": item.get("title") or "TikTok Video",
                        "uploader": item.get("author", {}).get("nickname") or "TikTok User",
                        "extractor": "tikwm"
                    }
                    
                    if item.get("images"):
                        info["entries"] = [{"url": u, "ext": "jpg"} for u in item["images"]]
                        info["type"] = "album"
                    else:
                        info["url"] = item.get("play") or item.get("wmplay")
                        info["ext"] = "mp4"
                    return info
        except Exception as e:
            LOGS.debug(f"Extractor | TikWM API error: {e}")
        return {"error": "TikWM API failed"}

# Global Instance
extractor = MediaExtractor()
