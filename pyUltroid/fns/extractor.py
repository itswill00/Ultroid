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
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            }
        }
        
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
        else:
            opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = "mp4"

        if custom_opts:
            opts.update(custom_opts)
            
        if progress_callback:
            opts["progress_hooks"] = [progress_callback]
            
        return opts

    @run_async
    def extract(self, url):
        """Extract metadata without downloading."""
        with YoutubeDL(self.get_opts()) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None
                return info
            except Exception as e:
                LOGS.warning(f"Extraction failed for {url}: {e}")
                return None

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
