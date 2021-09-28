"""
Private Music bot originally created by Valentin B.
Link: https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d

Update and Develop by Tpmonkey for Education purpose.
"""

import os
import enum
import asyncio
import datetime
import itertools
import math
import random
import logging

import discord
from async_timeout import timeout
from discord.ext import commands

# YouTube Playlist
import googleapiclient.discovery
from urllib.parse import parse_qs, urlparse

# YouTube DL
from utils.audio import YTDLSource, YTDLError

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

log = logging.getLogger(__name__)

class Loop(enum.Enum):
    NONE = 0
    SINGLE = 1
    QUEUE = 2

class VoiceError(Exception):
    pass           


class PlaylistSong:
    """
    A Singleton class for storing Playlist Song in case of a ton of songs is queued in a short peroid of time.
    """
    _loaded = {}
    # __slots__ = ("url", "ctx", "song")

    def __new__(cls, url: str, ctx: commands.Context):
        if (a := cls._loaded.get(url)) is not None:
            a.ctx = ctx
            return a
        
        a = super().__new__(cls)
        cls._loaded[url] = a
        a._init(url, ctx)
        return a        

    def _init(self, url: str, ctx: commands.Context):
        self.url = url
        self.ctx = ctx
        self.song = None        

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
            color = discord.Color.random(), # Nice
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

class LoadPlaylistSong:
    def __init__(self, bot: commands.Bot):
        self.queue = SongQueue()
        self.bot = bot

        self.loader = bot.loop.create_task(self.load())
    
    async def load(self):
        while True:
            loading = await self.queue.get()

            try:
               source = await YTDLSource.create_source(loading.ctx, loading.url)
            except:
                # In case of rate limit, wait a bit before retrying anothe song
                await asyncio.sleep(1.0)
            else:
                loading.song = Song(source)

            await asyncio.sleep(
                1.2 * len(self.bot.get_cog("Music").voice_states)
            )
    
    async def put(self, song: PlaylistSong):
        self.queue.put_nowait(song)


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        log.debug(f"VoiceState created for {ctx.guild.id}")
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()
        self.loader = LoadPlaylistSong(bot)

        self.super_shuffle = False
        self._loop = Loop.NONE
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())
        

    def __del__(self):
        self.audio_player.cancel()
        self.loader.loader.cancel()

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
        log.info(f"Audio Player Launched for {self._ctx.guild.id}")
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
                if self.current.song is None:
                    try:
                        source = await YTDLSource.create_source(self.current.ctx, self.current.url, loop=self.bot.loop)
                    except Exception:
                        await self._ctx.send(f":x: **Unable to load:** {self.current.url}")
                        continue
                    self.current = Song(source)
                else:
                    self.current = self.current.song

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
        self.loader.queue.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    """
    Music system
    **Note:** All commands are like Groovy, Rythm bot except remove command is changed to `,removes`
    """
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

    @commands.command(name="musicdebug", hidden=True)
    @commands.is_owner()
    async def _music_debug(self, ctx: commands.Context):
        text = f"Total of {len(self.voice_states)}\n"
        text += "\n".join([str(i) for i in self.voice_states])
        await ctx.send(text)

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

    @commands.command(name='join', aliases=['summon', ], invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            try:
                await ctx.voice_client.move_to(None)
            except:
                try:
                    for x in self.bot.voice_clients:
                        if(x.guild == ctx.guild):
                            return await x.disconnect()
                except:
                    return await ctx.send(':x: **Not connected to any voice channel.**')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

        await ctx.message.add_reaction("👋")

    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, volume: int = None):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send(':x: **Nothing being played at the moment.**')
        
        if volume is None:
            return await ctx.send(f"**Current Volume:** {ctx.voice_state.volume * 100}%")

        if volume < 0 or volume > 100:
            return await ctx.send(':x: **Volume must be between 0 and 100**')

        ctx.voice_state.volume = volume / 100
        try:
            ctx.voice_state.current.source.volume = volume / 100
        except:
            pass

        await ctx.send('**Volume of the player set to {}%**'.format(volume))

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        if hasattr(ctx.voice_state.current, "create_embed"):
            await ctx.send(embed=ctx.voice_state.current.create_embed())
        else:
            await ctx.send(":x: **Nothing being play at the moment!** ¯\_(ツ)_/¯")

    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.voice.is_playing(): # not ctx.voice_state.is_playing and
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume', invoke_without_subcommand=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.voice.is_paused(): # not ctx.voice_state.is_playing and
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop', aliases=['clear'])
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()
        ctx.voice_state.loop = Loop.NONE
        ctx.voice_state.loader.queue.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send(':x: **Not playing any music right now...**')

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
            await ctx.send(':x: **You have already voted to skip this song.** ._.')

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.

        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0 and ctx.voice_state.current is None:
            return await ctx.send(':x: **Empty queue.**')

        items_per_page = 8
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        if pages + 1 == page:
            # display queue even if there is only 1 song being play.
            pass
        elif 0 < page > pages:
            return await ctx.send(":x: **Page is out of range!**")

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            if isinstance(song, Song):
                queue += '**{0}.** [{1.source.title}]({1.source.url})\n'.format(i + 1, song)
            else:
                if song.song is not None:
                    queue += '**{0}.** [{1.song.source.title}]({1.song.source.url})\n'.format(i + 1, song)
                else:
                    queue += f"**{i+1}.** [Couldn't load this song]({song.url})\n"

        queue = queue or "Nothing \:("

        embed = (
            discord.Embed(
                title = f"Queue for {ctx.guild}",
                description='**{} tracks:**\nLoop: {} | Loop Queue: {} | Super Shuffle: {}'.format(
                    len(ctx.voice_state.songs) + 1, 
                    "✅" if ctx.voice_state.loop == Loop.SINGLE else "❌" ,
                    "✅" if ctx.voice_state.loop == Loop.QUEUE else "❌" ,
                    "✅" if ctx.voice_state.super_shuffle else "❌" ,
                    ),
                colour = discord.Colour.random(),
                timestamp = ctx.message.created_at
            )
            .set_footer(text='Viewing page {}/{}'.format(page, pages))
        )

        current = ctx.voice_state.current
        embed.add_field(name = "Current:", value = f"[{current.source.title}]({current.source.url})", inline=False)

        embed.add_field(name="Up Next:", value = queue)

        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(':x: **Empty queue.**')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')
    
    @commands.command(name="sshuffle")
    async def _sshuffle(self, ctx: commands.Context):
        """Shuffles the queue everytimes the song ended."""
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(':x: **Not enough song to enable this!**')

        ctx.voice_state.super_shuffle = not ctx.voice_state.super_shuffle
        await ctx.send(
            f"✅ **Turn {'on' if ctx.voice_state.super_shuffle else 'off'} super shuffle!**"
        )


    @commands.command(name='removes')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(':x: **Empty queue.**')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.

        Invoke this command again to unloop the song.
        """
        
        for i in range(5):
            if ctx.voice_state.current is None:
                await asyncio.sleep(0.5)
                continue         
            break
        else:
            return await ctx.send(':x: **Nothing being played at the moment.**')

        if ctx.voice_state.loop == Loop.NONE:
            ctx.voice_state.loop = Loop.SINGLE
            await ctx.send(":repeat_one: **Now Looping Current Song!**")
        elif ctx.voice_state.loop ==  Loop.SINGLE:
            ctx.voice_state.loop = Loop.QUEUE
            await ctx.send(":repeat: **Now Looping Queue!**")
        else:
            ctx.voice_state.loop = Loop.NONE
            await ctx.send("**Disable Looping!**")
    
    @commands.command(name='loopqueue', aliases=['loopq', 'lq'])
    async def _loopq(self, ctx: commands.Context):
        """Loops the entire queue.

        Invoke this command again to unloop the queue.
        """

        for i in range(5):
            if ctx.voice_state.current is None:
                await asyncio.sleep(0.5)
                continue         
            break
        else:
            return await ctx.send(':x: **Nothing being played at the moment.**')

        if ctx.voice_state.loop == Loop.SINGLE or ctx.voice_state.loop == Loop.NONE:
            ctx.voice_state.loop = Loop.QUEUE
            await ctx.send(":repeat: **Now Looping Queue!**")
        else:
            ctx.voice_state.loop = Loop.NONE
            await ctx.send("**Disable Looping!**")
        

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str = None):
        """Plays a song.

        If there are songs in the queue, this will be queued until the
        other songs finished playing.

        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)
        
        if search is None:
            return await ctx.invoke(self._resume)

        log.debug(f"{ctx.guild.id}: Searching {search}")
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
                    pl = PlaylistSong(s, ctx)
                    await ctx.voice_state.songs.put(pl)
                    await ctx.voice_state.loader.put(pl)
                    amount += 1
                
                await asyncio.sleep(1)
                await ctx.send("Enqueued {} songs.".format(amount))
                
            else:
                """pl = PlaylistSong(ctx, search)
                await ctx.voice_state.songs.put(pl)
                await ctx.voice_state.loader.put(pl)"""
                try:
                    source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
                except YTDLError as e:
                    await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
                else:
                    song = Song(source)

                    await ctx.voice_state.songs.put(song)
                    await ctx.send('Enqueued {}'.format(str(source)))
            log.debug(f"Enqueued")

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError(':x: **You are not connected to any voice channel.**')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError(':x: **Bot is already in a voice channel.**')


def setup(bot):
    bot.add_cog(Music(bot))