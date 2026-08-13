"""
downloader.py
YouTube Downloader Anti-Bot untuk AI Clipper
"""

import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

import yt_dlp

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

def _build_base_ydl_opts(output_path: str) -> dict[str, Any]:
    ua = random.choice(USER_AGENTS)
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    has_ffmpeg = shutil.which("ffmpeg") is not None

    ydl_opts: dict[str, Any] = {
        "outtmpl": output_path,
        "retries": 10,
        "fragment_retries": 10,
        "ignoreerrors": False,
        "user_agent": ua,
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "web_embedded"],
                "skip": ["webpage"],
            }
        },
        "remote_components": ["ejs:github"],  # Fix: Must be a List, not string
        "throttledratelimit": 1000000,
        "sleep_interval": 3,
        "max_sleep_interval": 10,
        "headers": {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.youtube.com/",
            "Origin": "https://www.youtube.com",
        },
        "verbose": False,
        "quiet": False,
        "no_warnings": False,
    }

    # Jika FFmpeg terinstall di OS/environment, izinkan merging high-quality video+audio
    if has_ffmpeg:
        ydl_opts["merge_output_format"] = "mp4"
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }]
    else:
        # Fallback: Ambil format pre-merged tunggal agar tidak membutuhkan FFmpeg
        print("⚠️ FFmpeg tidak ditemukan di PATH. Menggunakan format single-stream (pre-merged)...")
        ydl_opts["format"] = "best[ext=mp4]/best"

    return ydl_opts


def _try_cookiefile_option(ydl_opts: dict[str, Any], cookie_file: str | None) -> bool:
    if cookie_file and Path(cookie_file).is_file():
        ydl_opts["cookiefile"] = str(cookie_file)
        print(f"🔐 Menggunakan cookies dari file: {cookie_file}")
        return True
    return False


def _try_cookies_from_browser(ydl_opts: dict[str, Any]) -> bool:
    browser_from_env = os.environ.get("YT_BROWSER")
    browser_profile = os.environ.get("YT_BROWSER_PROFILE")

    if browser_from_env:
        if browser_profile:
            ydl_opts["cookiesfrombrowser"] = (browser_from_env, browser_profile)
        else:
            ydl_opts["cookiesfrombrowser"] = (browser_from_env,)
        return True

    for b in ("chrome", "safari", "firefox"):
        ydl_opts["cookiesfrombrowser"] = (b,)
        return True

    return False


class DownloadError(Exception):
    """Raised when a YouTube download operation fails."""


def download_youtube(
    url: str,
    output_path: str,
    use_cookies: bool = True,
    cookie_file: str | None = None,
) -> str:
    if not url or not url.startswith("http"):
        raise ValueError(f"URL tidak valid: {url}")

    ydl_opts = _build_base_ydl_opts(output_path)

    if use_cookies:
        cookies_applied = _try_cookiefile_option(ydl_opts, cookie_file)
        if not cookies_applied:
            cookies_applied = _try_cookiefile_option(ydl_opts, os.environ.get("COOKIES_FILE"))
        if not cookies_applied:
            _try_cookies_from_browser(ydl_opts)

    time.sleep(random.uniform(1.0, 3.0))

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"⬇️  Mulai download: {url}")
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise Exception("yt-dlp gagal mendapatkan info video.")
            title = info.get("title") or "Unknown title"
            print(f"✅ Download selesai: {title}")
            return output_path
    except yt_dlp.utils.DownloadError as e:
        raise DownloadError(f"Download gagal: {e}") from e


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python downloader.py <youtube_url> <output_path>")
        sys.exit(1)
    download_youtube(sys.argv[1], sys.argv[2])