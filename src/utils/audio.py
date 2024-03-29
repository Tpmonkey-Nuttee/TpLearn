import asyncio
import functools
import json
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import discord
import googleapiclient.discovery
import yt_dlp

# Silence useless bug reports messages
yt_dlp.utils.bug_reports_message = lambda: ''

__all__ = (
    "POOL", "YTDLError", "YTDLSource", "DownloadError", "getYtPlaylist", "getInfo", "YOUTUBE_API_KEY", "YOUTUBE_PLAYLIST_KEYWORDS", "youtubeapi"
)

POOL = ThreadPoolExecutor()

YOUTUBE_PLAYLIST_KEYWORDS = ("youtube.com/playlist?", "&start_radio", "&list=")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if YOUTUBE_API_KEY is None:
    raise ImportError(
        "Youtube API key is not set, Please head to https://console.cloud.google.com/apis/ to setup one."
    )

youtubeapi = True
try:
    youtube = googleapiclient.discovery.build(
        "youtube", "v3",
        developerKey=YOUTUBE_API_KEY,
        static_discovery=False
    )
    _search = youtube.search()
    _playlistItems = youtube.playlistItems()
except Exception:
    youtubeapi = False


chars = {
    "&quot;": '"',
    "&#39;": "'",
    "&amp;": "&"
}

COOKIES = os.getenv("Cookies")


@lru_cache(maxsize=None)
def getInfo(q: str) -> dict:
    _ = _search.list(
        q=q,
        part="id,snippet",
        type="video",
        maxResults=1
    ).execute()

    _ = _['items'].pop(0)

    # Youtube API is just weird.
    title = _['snippet']['title']
    for text in chars:
        if text in title:
            title = title.replace(text, chars[text])

    _['snippet']['title'] = title
    return _


@lru_cache(maxsize=None)
def getYtPlaylist(url: str) -> Tuple[List[str]]:
    # actually get playlist id
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    playlist_id = query["list"][0]

    request = _playlistItems.list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50  # 50 vid per request.
    )
    response = request.execute()
    maximum = 1 if "&start_radio" in url else 8

    playlist_items = []
    current = 0
    while request is not None:  # there're more vid to fetch? get it all!!!!
        response = request.execute()
        playlist_items += response["items"]
        request = youtube.playlistItems().list_next(request, response)

        current += 1
        if current >= maximum:  # it's too much now... stop at 200 vid.
            break

    # get title and the urls.
    sources = [
        f'https://www.youtube.com/watch?v={t["snippet"]["resourceId"]["videoId"]}' for t in playlist_items
    ]
    titles = [t["snippet"]["title"] for t in playlist_items]

    return sources, titles


class YTDLError(Exception):
    pass


DownloadError = yt_dlp.DownloadError


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': True,
        'extract_flat': True,
        'skip_download': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',  # ipv6 addresses cause issues sometimes
        'force-ipv4': True,
        'cachedir': False,
        "cookiefile": COOKIES,
        'preferredcodec': 'mp3',
        # 'noplaylist': True,
    }

    # For reference.
    # FFMPEG_DEFAULT_OPTIONS = {
    #    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    #    'options': '-vn -filter:a "asetrate=44100*{pitch},aresample=44100,atempo={speed}/{pitch}"',
    # }

    __slots__ = "data", "uploader", "uploader_url", \
        "date", "upload_date", "title", "thumbnail", "description", "duration", "tags", \
        "url", "views", "likes", "dislikes", "stream_url"

    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5, speed: float = 1):
        super().__init__(source, volume)
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')

        raw_duration = data.get("duration")
        if raw_duration is None:
            raise YTDLError(
                "Invalid video duration. (Video not found or We messed up)")
        self.raw_duration = int(raw_duration * 1/speed)
        self.duration = self.parse_duration(self.raw_duration)

        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, search: str, *, loop: Optional[asyncio.BaseEventLoop] = None, speed: float = 1, pitch: float = 1):
        loop = loop or asyncio.get_event_loop()

        webpage_url = search  # process_info['webpage_url']
        cls.ytdl.cache.remove()
        partial = functools.partial(
            cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(POOL, partial)

        if processed_info is None:
            raise YTDLError(f'Couldn\'t fetch `{webpage_url}`')

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError(
                        f'Couldn\'t retrieve any matches for `{webpage_url}`'
                    )

        if info.get('is_live'):
            raise YTDLError("Couldn't fetch live video.")

        division = min(max(speed / pitch, 0.5), 100)
        division = f",atempo={division}" if division != 1 else ""
        asetrate = ",asetrate=44100" if pitch == 1 else f",asetrate=44100*{pitch}"

        print("Created Source YouTubeDL", division, asetrate,
              search.strip("https://www.youtube.com/watch?"))

        opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': f'-vn -filter:a "aresample=44100{asetrate}{division}"',
        }

        return cls(discord.FFmpegPCMAudio(source=info['url'], **opts), data=info, speed=speed)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []

        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)
