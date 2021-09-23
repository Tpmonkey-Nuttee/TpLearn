"""
Private Music bot originally created by Valentin B.
Link: https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d

Update and Develop by Tpmonkey for Education purpose.
"""

import os
import enum
import asyncio
import datetime
import functools
import itertools
import math
import random

import discord
import youtube_dl
from async_timeout import timeout
from discord.ext import commands

import googleapiclient.discovery
from urllib.parse import parse_qs, urlparse

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

class Loop(enum.Enum):
    NONE = 0
    SINGLE = 1
    QUEUE = 2

class VoiceError(Exception):
    pass

class YTDLError(Exception):
    pass


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
        print("Creating Source YouTubeDL")
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
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
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
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
        print("Created Source YouTubeDL")
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

class PlaylistSong:
    """
    A place holder for Playlist system. The song won't be load until it's at its queue.
    After it's loaded, It will be <class 'Song'> instead.
    """
    __slots__ = ("url", "ctx")

    def __init__(self, ctx: commands.Context, url: str):
        self.url = url
        self.ctx = ctx

class Song:
    """Song class for storing the Source and Requester"""
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource = None, url: str = None):

        self.source = source
        self.requester = source.requester


    def create_embed(self):
        embed = discord.Embed(
            title = "Now Playing",
            description = f"[**{self.source.title}**]({self.source.url})",
            color = discord.Color.random(seed=69), # Nice
            timestamp = datetime.datetime.utcnow()
        )

        embed.add_field(name='Duration', value=self.source.duration)
        embed.add_field(name='Requested by', value=self.requester.mention)

        embed.set_thumbnail(url=self.source.thumbnail)
        embed.set_footer(text="Use ,p <song> to add more!")

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self.super_shuffle = False
        self._loop = Loop.NONE
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: Loop):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current    

    async def audio_player_task(self):
        print("Audio Player created!")
        while True:
            self.next.clear()

            if self._loop == Loop.NONE:
                # Try to get the next song within timeout limit (defeault 3 mins).
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:                    
                    async with timeout(self.bot.msettings.get(self._ctx.guild.id, "timeout")):
                        self.current = await self.songs.get()
                    
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            else:
                # If loop is on, get the source again. I don't know why but apparently 
                # You can't use the same source twice, you need to create a new source everytime :/

                song = None
                if not isinstance(self.current, PlaylistSong):
                    try:
                        source = await YTDLSource.create_source(self._ctx, self.current.source.url, loop=self.bot.loop)
                    except YTDLError as e:
                        await self._ctx.send('An error occurred while processing this request: {}'.format(str(e)))
                    song = Song(source)

                if self._loop == Loop.SINGLE:
                    # Set the current song to be the same as last one.
                    # So it will play the same song again and again
                    self.current = song
                elif self._loop == Loop.QUEUE:
                    # Loop queue simply work by putting the ended song at the end of the queue.
                    if song is not None:
                        await self.songs.put(song)
                    self.current = await self.songs.get()
            
            if isinstance(self.current, PlaylistSong):
                try:
                    source = await YTDLSource.create_source(self.current.ctx, self.current.url, loop=self.bot.loop)
                except Exception:
                    await self._ctx.send(f"Unable to load: {self.current.url}")
                    continue
                self.current = Song(source)

            if self.super_shuffle:
                self.songs.shuffle()
            # Set the volume, that nobody cares and play it
            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)

            # If option "annouce next song" is on, annouce it
            if self.bot.msettings.get(self._ctx.guild.id, "annouce_next_song"):
                await self.current.source.channel.send(embed=self.current.create_embed())     

            await self.next.wait()

    def play_next_song(self, error=None):
        # Call when the song ended or and exception has been raised
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        # Clear SKip Votes (set)
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # For keeping track of all voice states
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        # Get voice state and embeded it to context.
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        error.handled = True # So error_handle won't be call and send message twice
        await ctx.send(':x: **An error occurred:** {}'.format(str(error)))
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        # Prevend force disconnect the bot from breaking the bot.
        if member.id != self.bot.user.id:
            return

        if before.channel is not None and after.channel is None:
            if member.guild.id in self.voice_states:
                await self.voice_states[member.guild.id].stop()
                del self.voice_states[member.guild.id]


    @commands.command(name="settings")
    async def _settings(self, ctx: commands.Context, name: str = None, value: int = None):
        """Music Settings."""

        if name is None:
            embed = discord.Embed(
                title = "Music Settings",
                colour = discord.Colour.default(),
                timestamp = ctx.message.created_at
            )

            settings = self.bot.msettings[str(ctx.guild.id)]
            for sett in settings:
                embed.add_field(
                    name = sett.replace("_", " ").title(),
                    value = settings[sett],
                    inline = False
                )

            await ctx.send(embed=embed)
        elif name is not None and value is not None:
            try:
                name = name.replace(" ", "_").lower()
                self.bot.msettings.set(ctx.guild.id, name, value)
            except ValueError:
                return await ctx.send(":x: **Invalid Setting name or Value**")
            await ctx.send("Successfully save new settings!")
        else:
            await ctx.send(":x: **Value is a must have argument!**")

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return


        ctx.voice_state.voice = await destination.connect()


    @commands.command(name='summon')
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.

        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, volume: int = None):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')
        
        if volume is None:
            return await ctx.send(f"Current Volume: {ctx.voice_state.volume * 100}%")

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        try:
            ctx.voice_state.current.source.volume = volume / 100
        except:
            pass

        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        if hasattr(ctx.voice_state.current, "create_embed"):
            await ctx.send(embed=ctx.voice_state.current.create_embed())
        else:
            await ctx.send("Nothing being play at the moment! ¯\_(ツ)_/¯")

    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.voice.is_playing(): # not ctx.voice_state.is_playing and
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.voice.is_paused(): # not ctx.voice_state.is_playing and
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop', aliases=['clear'])
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester or not self.bot.msettings.get(ctx.guild.id, "vote_skip"):
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            needed_votes = int(len([i for i in ctx.author.voice.channel.members if not i.bot]) * 0.5 // 1)
            print(needed_votes)

            if total_votes >= needed_votes:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/{}**'.format(total_votes, needed_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.

        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            if isinstance(song, Song):
                queue += '**{0}.** [{1.source.title}]({1.source.url})\n'.format(i + 1, song)
            else:
                queue += f"**{i+1}.** [Not yet loaded]({song.url})\n"

        embed = (
            discord.Embed(
                description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue),
                colour = discord.Colour.random(),
                timestamp = ctx.message.created_at
            )
            .set_footer(text='Viewing page {}/{}'.format(page, pages))
        )
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')
    
    @commands.command(name="sshuffle")
    async def _sshuffle(self, ctx: commands.Context):
        """Shuffles the queue everytimes the song ended."""
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.super_shuffle = not ctx.voice_state.super_shuffle
        await ctx.send(
            f"✅ Turn {'on' if ctx.voice_state.super_shuffle else 'off'} super shuffle!"
        )


    @commands.command(name='removes')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.

        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')


        if ctx.voice_state.loop == Loop.NONE:
            ctx.voice_state.loop = Loop.SINGLE
            await ctx.send(":repeat_one: Now Looping Current Song!")
        elif ctx.voice_state.loop ==  Loop.SINGLE:
            ctx.voice_state.loop = Loop.QUEUE
            await ctx.send(":repeat: Now Looping Queue!")
        else:
            ctx.voice_state.loop = Loop.NONE
            await ctx.send("Disable Looping!")
    
    @commands.command(name='loopqueue')
    async def _loopq(self, ctx: commands.Context):
        """Loops the entire queue.

        Invoke this command again to unloop the queue.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if ctx.voice_state.loop == Loop.SINGLE or ctx.voice_state.loop == Loop.NONE:
            ctx.voice_state.loop = Loop.QUEUE
            await ctx.send(":repeat: Now Looping Queue!")
        else:
            ctx.voice_state.loop = Loop.NONE
            await ctx.send("Disable Looping!")
        

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.

        If there are songs in the queue, this will be queued until the
        other songs finished playing.

        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            if "youtube.com/playlist?" in search or "&start_radio" in search: 
                query = parse_qs(urlparse(search).query, keep_blank_values=True)
                playlist_id = query["list"][0]

                youtube = googleapiclient.discovery.build("youtube", "v3", developerKey = YOUTUBE_API_KEY)

                request = youtube.playlistItems().list(
                    part = "snippet",
                    playlistId = playlist_id,
                    maxResults = 25
                )
                response = request.execute()
                
                maximum = 8
                if "&start_radio" in search:
                    maximum = 1

                playlist_items = []
                current = 0
                while request is not None:
                    response = request.execute()
                    playlist_items += response["items"]
                    request = youtube.playlistItems().list_next(request, response)

                    current += 1
                    if current >= maximum:
                        break
                
                sources = [f'https://www.youtube.com/watch?v={t["snippet"]["resourceId"]["videoId"]}&list={playlist_id}&t=0s' for t in playlist_items]
                amount = 0

                for s in sources:
                    """print("Loading", s)
                    try:
                        source = await YTDLSource.create_source(ctx, s, loop=self.bot.loop)   
                    except Exception as e:
                        print("Error, passing", e)
                        await ctx.send(f'An error occurred while loading a song ({s})\nI will skip it!')
                        continue
                    else:
                        song = Song(source)   """      

                    await ctx.voice_state.songs.put(PlaylistSong(ctx, s))
                    amount += 1
                
                return await ctx.send("Enqueued {} songs.".format(amount))
                
            else:
                try:
                    source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
                except YTDLError as e:
                    await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
                else:
                    song = Song(source)

                    await ctx.voice_state.songs.put(song)
                    await ctx.send('Enqueued {}'.format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')


def setup(bot):
    bot.add_cog(Music(bot))