import discord
from discord.ext import commands

import youtube_dl

# YouTube Playlist
import googleapiclient.discovery
from urllib.parse import parse_qs, urlparse

import asyncio
import functools

from typing import List, Tuple

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''

__all__ = (
    "YTDLError", "YTDLSource", "DownloadError", "getYtPlaylist", "getInfo", "YOUTUBE_API_KEY", "YOUTUBE_PLAYLIST_KEYWORDS"
)

import os

YOUTUBE_PLAYLIST_KEYWORDS = ("youtube.com/playlist?", "&start_radio", "&list=")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if YOUTUBE_API_KEY is None:
    raise ImportError(
        "Youtube API key is not set, Please head to https://console.cloud.google.com/apis/ to setup one."
    )



youtube = googleapiclient.discovery.build("youtube", "v3", developerKey = YOUTUBE_API_KEY)
_search = youtube.search()
_playlistItems = youtube.playlistItems()


def getInfo(q: str) -> dict:
    return _search.list(
        q = q,
        part = "id,snippet",
        maxResults = 1
    ).execute()['items'].pop(0)

def getYtPlaylist(url: str) -> Tuple[List[str]]:
    # actually get playlist id
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    playlist_id = query["list"][0]
    
    request = _playlistItems.list(
        part = "snippet",
        playlistId = playlist_id,
        maxResults = 50 # 50 vid per request.
    )
    response = request.execute()    
    maximum = 1 if "&start_radio" in url else 8

    playlist_items = []
    current = 0
    while request is not None: # there're more vid to fetch? get it all!!!!
        response = request.execute()
        playlist_items += response["items"]
        request = youtube.playlistItems().list_next(request, response)

        current += 1
        if current >= maximum: # it's too much now... stop at 200 vid.
            break

    # get title and the urls.
    sources = [f'https://www.youtube.com/watch?v={t["snippet"]["resourceId"]["videoId"]}&list={playlist_id}' for t in playlist_items]
    titles = [t["snippet"]["title"] for t in playlist_items]

    return sources, titles

class YTDLError(Exception):
    pass

DownloadError = youtube_dl.DownloadError

class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        "cookiefile": "com_cookies.txt",
        "cachedir": False,
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }
    FFMPEG_OPTIONS_NC = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "atempo=1.25,asetrate=44100*1.25"',
    }

    __slots__ = "data", "uploader", "uploader_url", \
        "date", "upload_date", "title", "thumbnail", "description", "duration", "tags", \
        "url", "views", "likes", "dislikes", "stream_url"

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)


        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, search: str, *, loop: asyncio.BaseEventLoop = None, nc: bool = False):
        loop = loop or asyncio.get_event_loop()

        webpage_url = search # process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))
        
        if info.get('is_live'):
            raise YTDLError("Couldn't fetch live video.")

        print("Created Source YouTubeDL", search.strip("https://www.youtube.com/watch?"))

        FFMPEG_OPTS = cls.FFMPEG_OPTIONS_NC if nc else cls.FFMPEG_OPTIONS
        return cls(discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTS), data=info)

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