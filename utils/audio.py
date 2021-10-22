import discord
from discord.ext import commands

import youtube_dl

import asyncio
import functools

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''

__all__ = ("YTDLError", "YTDLSource", "DownloadError", "getTracks", "getAlbum", "getRecommend")

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
        "cachedir": False
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
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
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        # This bit of code seems to do nothing except make the load time longer.
        # To be sure, I will just comment it out and if somethign went wrong, I will check it again.
        """partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))"""

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
        
        if info['is_live']:
            raise YTDLError("Couldn't fetch live video.")

        print("Created Source YouTubeDL", search.strip("https://www.youtube.com/watch?"))
        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

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

# Spotify library.
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import os

cid = os.getenv("CID")
secret = os.getenv("SECRET")

# Creating and authenticating our Spotify app.
client_credentials_manager = SpotifyClientCredentials(cid, secret)
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def getTracks(playlistURL):   
    # Getting a playlist.
    results = spotify.user_playlist_tracks(user="",playlist_id=playlistURL, offset=0)

    trackList = []
    offset = 0
    
    # Loop untils all the tacks are extracted from playlist.
    # The reason behind is, Spotify API has limit at 100 tracks at a time, 
    # So to work around, We use offset insated
    while len(results["items"]) != 0:
        for i in results["items"]:
            artist = i["track"]["artists"][0]["name"]
            name = i["track"]["name"]

            trackList.append(f"{name} {artist}")

        offset += 100

        # Get it again, with an offset
        results = spotify.user_playlist_tracks(user="",playlist_id=playlistURL, offset=offset)

    return trackList

def getAlbum(albumURL):
    # Getting a album.
    results = spotify.album_tracks(albumURL, offset=0)

    trackList = []
    offset = 0

    # For each track in the album.
    while len(results["items"]) != 0:
        for i in results["items"]:
            artist = i["artists"][0]["name"]
            name = i["name"]

            trackList.append(f"{name} {artist}")
        offset += 50

        results = spotify.album_tracks(albumURL, offset=offset)

    return trackList

def getRecommend(names: list, amount: int = 20) -> list:    
    # Find uri
    uris = []
    for name in names:
        if "open.spotify.com/track/" in name:
            uris.append(name)
            continue

        r = spotify.search(q=name, limit=1)

        if len(r['tracks']['items']) == 0:
            continue
            
        uris.append(r['tracks']['items'][0]['uri'])
    
    if len(uris) == 0:
        raise NameError

    # find recommendations
    r = spotify.recommendations(seed_tracks=uris, limit=amount)
    trackList = []
    
    for i in r['tracks']:
        name = i['name']
        artist = i["artists"][0]["name"]

        trackList.append(f"{name} {artist}")
    
    return trackList