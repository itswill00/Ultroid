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

class MediaExtractor:
    def __init__(self, download_path="downloads/"):
        self.download_path = download_path
        if not os.path.exists(download_path):
            os.makedirs(download_path)

    def get_opts(self, custom_opts=None):
        opts = {
            "outtmpl": f"{self.download_path}%(title).20s_%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "noplaylist": True,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        }
        if custom_opts:
            opts.update(custom_opts)
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
    def download(self, url):
        """Download media and return the file path(s)."""
        opts = self.get_opts()
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
