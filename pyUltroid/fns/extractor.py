# Ultroid Media Extraction Engine
# Powered by yt-dlp

import os
import re
import asyncio
from pyUltroid import LOGS
from pyUltroid.fns.helper import run_async, bash
from yt_dlp import YoutubeDL

# Regex Patterns
TIKTOK_RE = re.compile(r"https?://(?:www\.|vm\.|vt\.)?tiktok\.com/\S+")
INSTAGRAM_RE = re.compile(r"https?://(?:www\.)?instagram\.com/(?:p|reels|reel|tv)/\S+")
TWITTER_RE = re.compile(r"https?://(?:www\.|mobile\.)?(?:twitter|x)\.com/\S+")
ADULT_RE = re.compile(r"https?://(?:www\.)?(?:pornhub\.com|xvideos\.com|xhamster\.com|xnxx\.com|spankbang\.com|eporner\.com)/\S+")

class MediaExtractor:
    def __init__(self, download_path="downloads/"):
        self.download_path = download_path
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        
        try:
            import yt_dlp
            LOGS.info(f"Extractor | Engine: yt-dlp v{yt_dlp.version.__version__}")
        except Exception:
            LOGS.warning("Extractor | Could not determine yt-dlp version.")

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
            "nocheckcertificate": True,
            "concurrent_fragment_downloads": 10,
            "buffersize": 1048576, # 1MB Buffer for VPS Throughput
            "extractor_args": {
                "youtube": {
                    "player_client": ["tv", "ios", "web"],
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
        }
        
        # Explicitly help yt-dlp find the newly installed node if it's in a non-standard path
        import shutil
        node_path = shutil.which("node")
        if node_path:
            opts["js_runtime"] = node_path
        
        # Check for Local Cookies to bypass YouTube bot detection
        if os.path.exists("cookies.txt"):
            try:
                with open("cookies.txt", "r") as f:
                    content = f.read(500)
                    if "# Netscape" not in content:
                        LOGS.warning("Extractor | cookies.txt is NOT in Netscape format!")
                    elif "\t" not in content and "  " in content:
                        LOGS.error("Extractor | cookies.txt detected SPACE-indentation instead of TABS! (Paste Error)")
                        LOGS.warning("Extractor | Re-upload cookies.txt via FTP/SFTP to preserve TABS.")
            except Exception as e:
                LOGS.warning(f"Extractor | Could not perform cookie integrity check: {e}")

            opts["cookiefile"] = "cookies.txt"
            LOGS.info("Extractor | cookies.txt detected and loaded.")
        else:
            LOGS.warning("Extractor | No cookies.txt found in root directory.")
        
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
        # Use more verbose options for metadata to catch VPS-specific blocks
        opts = self.get_opts(format_type="extract")
        opts.update({"quiet": False, "no_warnings": False})
        
        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    LOGS.error(f"Extractor | Null info returned for {url}")
                    return {"error": "YouTube returned no metadata (Empty)."}
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

    @run_async
    def download(self, url, format_type="video", job_id=None, progress_callback=None):
        """Download media and return the file path(s)."""
        if job_id:
            os.makedirs(os.path.join(self.download_path, job_id), exist_ok=True)
        opts = self.get_opts(format_type, job_id=job_id, progress_callback=progress_callback)
        with YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None
                
                # Handle single file
                if "entries" not in info:
                    return [ydl.prepare_filename(info)]
                
                # Handle multi-file (like TikTok slides or IG Carousel)
                files = []
                for entry in info["entries"]:
                    if entry:
                        files.append(ydl.prepare_filename(entry))
                return files
            except Exception as e:
                LOGS.error(f"Download failed for {url}: {e}")
                return None

# Global Instance
extractor = MediaExtractor()
