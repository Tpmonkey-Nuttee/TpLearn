"""
Private Music bot originally created by Valentin B.
Link: https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d

Update and Develop by Tpmonkey for Education purpose.
"""
import time
import enum
import math
import random
import logging
import asyncio
import datetime
import itertools
import traceback

import discord
from async_timeout import timeout
from discord.ext import commands, tasks

# Audio system (Youtube DL & Spotipy)
from utils.audio import *
from utils.spotify import *

log = logging.getLogger(__name__)

class Loop(enum.Enum):
    NONE = 0
    SINGLE = 1
    QUEUE = 2

class VoiceError(Exception):
    pass

class PlaylistSong:
    """Just a dataclass for storing Playlist song.
    """
    __slots__ = "url", "ctx", "title", "song"
    
    def __init__(self, url: str, ctx: commands.Context, title: str = None):
        self.url = url
        self.ctx = ctx
        self.title = title
        self.song = None         

class Song:
    """Song class for storing the Source and Requester
    """
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource = None, url: str = None):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        # Create embed containing detail of the song.
        embed = discord.Embed(
            title = "Now Playing",
            description = f"[{self.source.title}]({self.source.url})",
            color = discord.Color.random(), 
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
        log.debug(f"VoiceState created for {ctx.guild.id}")
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self.super_shuffle = False
        self.loading = False
        self._loop = Loop.NONE
        self._volume = 0.5
        self.skip_votes = set()
        self.announce_message = None

        self.playing = False
        self.audio_player = None # bot.loop.create_task(self.audio_player_task())     

    def __del__(self):
        if self.audio_player is not None:
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

    def start_player(self):
        self.playing = True
        if self.audio_player is None:
            self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    async def audio_player_task(self):
        # Note: This is madness. Who ever try to read this, Good luck.
        log.info(f"Audio Player Launched for {self._ctx.guild.id}")
        while True:
            self.next.clear()
            
            try:
                await self.announce_message.delete()
            except Exception:
                pass

            if self._loop == Loop.NONE:
                # Try to get the next song within timeout limit (defeault 3 mins).
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance reasons.
                try:                    
                    async with timeout(self.bot.msettings.get(self._ctx.guild.id, "timeout")):
                        self.current = await self.songs.get()
                    
                except asyncio.TimeoutError:
                    log.debug(f"{self._ctx.guild.id}: No more track, stopping")
                    return self.bot.loop.create_task(self.stop())

            else: # Loop is on                
                # Loop Logic: Try to load the ended song agian,
                # Then put it behind the queue if loop queue is enable
                # or Set current track to be the loaded song if loop single

                # Load current track again.
                try:
                    self.loading = True
                    source = await YTDLSource.create_source(self.current.source.ctx, self.current.source.url)
                except Exception:
                    await self._ctx.send(f"Couldn't load track & Removed from the queue.\n{self.current.source.url}")
                else:
                    song = Song(source)

                    if self._loop == Loop.SINGLE:
                        self.current = song
                    else: # Loop queue.
                        await self.songs.put(song)
                        self.current = await self.songs.get()
                finally:
                    self.loading = False
            
            if isinstance(self.current, PlaylistSong):
                # If It's playlist song and is not loaded yet, load it.
                try:
                    self.loading = True
                    source = await YTDLSource.create_source(self.current.ctx, self.current.url)
                except Exception:
                    log.info(f"{self._ctx.guild.id}: Unable to load playlist song, retrying...")
                    url = self.current.url

                    if "http" not in url: # It's actually the song name
                        try:
                            source = await YTDLSource.create_source(self.current.ctx, url+" lyric")
                        except Exception:
                            await self._ctx.send(f"Couldn't load track: {self.current.url}")
                            log.info(f"{self._ctx.guild.id}: Download fail, Skipped")
                            continue
                        log.info(f"{self._ctx.guild.id}: Sucessfully loaded the song, continue playing...")
                    else:
                        await self._ctx.send(f"Couldn't load track: {self.current.url}")
                        log.info(f"{self._ctx.guild.id}: It was an url, skipping...")
                        continue
                finally:
                    self.loading = False
                        
                self.current = Song(source)

            # super shuffle.
            if self.super_shuffle:
                self.songs.shuffle()

            # Set the volume, that nobody cares and play it
            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)            

            # If option "annouce next song" is on, annouce it
            if self.bot.msettings.get(self._ctx.guild.id, "annouce_next_song"):
                self.announce_message = await self.current.source.channel.send(embed=self.current.create_embed())    

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
        
        if self.audio_player is not None:
            self.audio_player.cancel()
        
        self.playing = False

        if self.voice:
            await self.voice.disconnect()
        
        # Delete "now playing" message.
        try:
            await self.announce_message.delete()
        except Exception:
            pass
        
        # Delete the reference
        cog = self.bot.get_cog("Music")
        if cog is not None:
            cog.remove_voicestate(self._ctx.guild.id)
        
        log.info(f"{self._ctx.guild.id}: Left vc & cleaned up")

class Music(commands.Cog):
    """Music system
    **Note:** All commands are like Groovy, Rythm bot except remove command is changed to `,removes`
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # For keeping track of all voice states
        self.voice_states = {}
        self.errors_count = {}

        # disconnecting when bot is alone, what a sad life.
        self.wait_for_disconnect = {}
        self.loop_for_deletion.start()
    
    def cog_unload(self) -> None:
        # when cog is unload (normally to reload command bc replit sucks)
        # stop all the loop and disconnect the bot from all vcs
        log.info("Unloading Cog")
        self.loop_for_deletion.stop() 
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())
    
    def remove_voicestate(self, key: int) -> None:
        self.voice_states.pop(key, None)
    
    def play_error(self, guild_id: int) -> None:
        count = self.errors_count.get(guild_id, 0)
        self.errors_count[guild_id] = count + 1
        
    def get_voice_state(self, ctx: commands.Context):
        # Get voice state and embeded it to context.
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state
        return state    

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM.')
        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        error.handled = True # So error_handle won't be call and send message twice
        await ctx.send(':x: **An error occurred:** {}'.format(str(error)))
    
    @tasks.loop(minutes=2)
    async def loop_for_deletion(self) -> None:        
        copy = self.wait_for_disconnect.copy()
        for gid in copy.keys():
            if time.time() >= self.wait_for_disconnect[gid]:
                log.info(f"{gid}: Timeout, Nobody left in vc... Disconnected")
                # Remove from current dict, But need to avoid RuntimeError
                # delete.append(gid)                

                # Leave channel & Clean up
                try:
                    await self.voice_states[gid].stop()
                except KeyError:
                    log.debug(f"{gid}: Attempted to disconnect but already disconnected.")
                else:
                    log.info(f"{gid}: Successfully disconnected")

                del self.wait_for_disconnect[gid]
        
        #for i in delete: 
        #    del self.wait_for_disconnect[i]

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        if member.guild.id not in self.voice_states:
            return
        
        # Bot disconnected?
        if member.id == self.bot.user.id and before.channel is not None and after.channel is None:
            voice_state = self.voice_states.get(member.guild.id)

            if voice_state is None:
                return
            
            if voice_state.playing:
                await asyncio.sleep(2)
                log.info(f"{member.guild.id}: Bot got disconnected why playing, Joining back!")
                voice_state.voice = await before.channel.connect()

            """if member.guild.id in self.wait_for_disconnect:
                # This is a mess, so I'm just gonna put sleep here.
                # It works, trust me.
                await asyncio.sleep(2)
                
                try:
                    del self.wait_for_disconnect[member.guild.id]
                except KeyError:
                    return

                log.info(f"{member.guild.id}: Bot got disconnected, removed wait for disconnect")
            return"""
        
        # Check if user switched to bot vc or joined the bot vc
        if (before.channel is None and after.channel is not None) or (before.channel != after.channel and after.channel is not None):
            all_members = [i.id for i in after.channel.members]

            # Wrong channel, go back
            if not self.bot.user.id in all_members: return

            # Remove bot timeout, so it won't disconnect.            
            try:
                del self.wait_for_disconnect[member.guild.id]
            except KeyError:                
                return
            log.info(f"{member.guild.id}: User joined back, Stopping deletion")
        
        # Check if user switched out from bot vc or left vc completelely.
        elif (before.channel is not None and after.channel is None) or  (before.channel != after.channel and before.channel is not None and after.channel is not None):
            all_members = [i.id for i in before.channel.members]

            # Wrong channel, go back
            if not self.bot.user.id in all_members: return

            # Bot is alone ;-;
            if len(all_members) <= 1:
                log.info(f"{member.guild.id}: All user left, Waiting for deletion")
                self.wait_for_disconnect[member.guild.id] = time.time() + self.bot.msettings.get(member.guild.id, "timeout")
    
    @staticmethod
    def shorten_title(title: str, url: str) -> str:
        # To make sure that embed field wouldn't contain more than 1024 letters.
        space_left = 110 - len(url)
        return title if len(title) < space_left else title[:space_left] + "..."

    @commands.command(name="settings")
    async def _settings(self, ctx: commands.Context, name: str = None, value: int = None):
        """Music Settings.
        """
        # No input, display all settings
        if name is None:
            embed = discord.Embed(
                title = "Music Settings",
                description = "To set boolean settings, use 1 as True and 0 as False.",
                colour = discord.Colour.default(),
                timestamp = ctx.message.created_at
            )
            # Get settings from bot, then add field one by one.
            settings = self.bot.msettings[str(ctx.guild.id)]
            for sett in settings:
                embed.add_field(
                    name = sett.replace("_", " ").title(),
                    value = settings[sett],
                    inline = False
                )
            await ctx.send(embed=embed)        
        
        elif name is not None and value is not None: # Set new settings
            try:
                name = name.replace(" ", "_").lower()
                if name == "timeout" and value <= 60:
                    return await ctx.send(":x: *imeout need to be more than 60 seconds!")

                try:
                    old = self.bot.msettings.get(ctx.guild.id, name)
                    self.bot.msettings.set(ctx.guild.id, name, value)
                    new = self.bot.msettings.get(ctx.guild.id, name)
                except KeyError:
                    return await ctx.send(":x: Unkown setting... Please try again later!")
                    
            except ValueError:
                return await ctx.send(":x: **Invalid Setting name or Value**")
            
            await ctx.send(f"Changed `{name}` from **{old}** to **{new}**")
        
        else: # Idk, are you drunk or what?
            await ctx.send(":x: **Value is a must have argument!**")

    @commands.command(name='join', aliases=['summon', ], invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel.
        """
        destination = ctx.author.voice.channel
        if ctx.voice_state.voice: # already connected to another channel.
            return await ctx.voice_state.voice.move_to(destination)
        ctx.voice_state.voice = await destination.connect()
        

    @commands.command(name='leave', aliases=['disconnect'])
    async def _leave(self, ctx: commands.Context, invoke_without_subcommand=True):
        """Clears the queue and leaves the voice channel.
        """
        if not ctx.voice_state.voice:
            # It's none, but maybe the bot just restarted.
            # so try to leave first.
            try:
                await ctx.voice_client.move_to(None)
            except Exception:
                # can't leave? try loop thru all the voice clients that is connected and then disconnect.
                # tbh, this doesn't work... but still at least I tried. :)
                try:
                    for x in self.bot.voice_clients:
                        if(x.guild == ctx.guild):
                            return await x.disconnect()
                except Exception: # Idk anymore
                    return await ctx.send("I'm not connected to any voice channel!")

        await ctx.voice_state.stop()
        log.debug(f"{ctx.guild.id}: stopped from leave command")
        await ctx.message.add_reaction("👋")

    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, volume: int = None):
        """Sets the volume of the player.
        """
        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment...')
        
        if volume is None:
            return await ctx.send(f"**Current Volume:** {ctx.voice_state.volume * 100}%")

        if volume < 0 or volume > 100:
            return await ctx.send(':x: **Volume must be between `0` and `100`**')

        ctx.voice_state.volume = volume / 100
        try: # try to change the current song, but maybe it's PlaylistSong so it doesn' loaded yet.
            ctx.voice_state.current.source.volume = volume / 100
        except AttributeError: pass

        await ctx.send('Volume of the player set to **{}%**'.format(volume))

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """Displays the current track.
        """
        if hasattr(ctx.voice_state.current, "create_embed"): # it's being played.
            await ctx.send(embed=ctx.voice_state.current.create_embed())
        else:
            await ctx.send("Nothing being play at the moment! ¯\_(ツ)_/¯")

    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        """Pauses.
        """
        if ctx.voice_state.voice.is_playing(): # if it's playing, pause else just ignore.
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume', invoke_without_subcommand=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes.
        """
        if ctx.voice_state.voice is None:
            return await ctx.send("I'm not connected to any voice channel!")

        if ctx.voice_state.voice.is_paused(): # if it's paused, resume else just ignore.
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop', aliases=['clear'])
    async def _stop(self, ctx: commands.Context):
        """Stops playing & Clears the queue."""
        # clear queue and set loop to none.
        ctx.voice_state.songs.clear()
        ctx.voice_state.loop = Loop.NONE

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')
    
    @commands.command(name='clearqueue', aliases=['clearq'])
    async def _clearq(self, ctx: commands.Context):
        """Clear queue but keep playing current track."""
        # well, I can use == 0 but I don't know why I used < 1
        # But I will leave it like this ;)
        if len(ctx.voice_state.songs) < 1:
            return await ctx.send("Queue is empty!")

        # clear queue.
        ctx.voice_state.songs.clear()
        await ctx.message.add_reaction('✅')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        half of all users in voice channel are needed for the song to be skipped.
        """
        if ctx.voice_state.audio_player is None:
            return await ctx.send('Nothing is playing!')

        voter = ctx.message.author

        # check if the person who voted is the requester or the setting "vote skip" is turned off.
        if voter == ctx.voice_state.current.requester or not self.bot.msettings.get(ctx.guild.id, "vote_skip"):
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        # normal vote skip.
        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            # need 50% of vc to agree not including bot.
            needed_votes = int(len([i for i in ctx.author.voice.channel.members if not i.bot]) * 0.5 // 1)

            if total_votes >= needed_votes: # reached 50%, skip it
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else: # waiting for more people to skip
                await ctx.send('Skip vote added, currently at **{}/{}**'.format(total_votes, needed_votes))

        else:
            await ctx.send('You have already voted! ._.')
    
    @commands.command(name="skipto")
    async def _skipto(self, ctx: commands.Context, index: int):
        """Skip to the index track.
        """
        if len(ctx.voice_state.songs) < 2:
            return await ctx.send("You need at least 2 tracks in queue to use this command!")
        
        # to work around the "asyncio.Queue" we need to dig deep into the actual code itself.
        # from https://github.com/python/cpython/blob/main/Lib/asyncio/queues.py#L48
        # I found out that the queue is based on `collections.deque()` so I access the attribute directly and use its method.
        # from https://docs.python.org/3/library/collections.html#collections.deque
        ctx.voice_state.songs._queue.rotate(-(index-1))
        # skip the current one
        ctx.voice_state.skip()        
        await ctx.message.add_reaction('✅')        

    @commands.command(name='queue', aliases=['q', 'list'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """
        if len(ctx.voice_state.songs) == 0 and ctx.voice_state.current is None:
            return await ctx.send('Empty queue. ¯\_(ツ)_/¯')
        
        if ctx.voice_state.loading:
            m = await ctx.send("Song is currently loading...")
            while ctx.voice_state.loading:
                await asyncio.sleep(0.5)
            await m.delete()

        items_per_page = 8
        pages = max(1, math.ceil(len(ctx.voice_state.songs) / items_per_page)) # use max to prevent 1/0 page

        if pages + 1 == page:
            # display queue even if there is only 1 song being play.
            pass
        elif 0 < page > pages:
            return await ctx.send(f"Page is out of range, I currently have {pages}.")

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            if isinstance(song, Song):      # requested one by one
                title = self.shorten_title(song.source.title, song.source.url)
                queue += '**{0}.** [{1}]({2.source.url})\n'.format(i + 1, title, song)
            else:
                if song.song is not None:    # is loaded
                    title = self.shorten_title(song.song.source.title, song.song.source.url)
                    queue += '**{0}.** [{1}]({2.song.source.url})\n'.format(i + 1, title, song)
                elif song.title is not None:
                    title = self.shorten_title(song.title, song.url)
                    queue += '**{0}.** [{1}]({2.url})\n'.format(i + 1, title, song) 
                elif "http" in song.url:     # not loaded, but have the url
                    queue += f"**{i+1}.** [Couldn't load this song]({song.url})\n"  
                else:                        # not loaded, have song name
                    queue += '**{0}.** {1.url}\n'.format(i + 1, song)

        queue = queue or "Nothing \:("
        # A large embed... madness
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

        if ctx.voice_state.current is not None: # check if it's currently playing something.
            current = ctx.voice_state.current
            embed.add_field(name = "Current:", value = f"[{current.source.title}]({current.source.url})", inline=False)
        else:
            embed.add_field(name = "Current:", value = "Nothing \:(", inline=False)

        embed.add_field(name="Up Next:", value = queue)

        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue.
        """
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue. ¯\_(ツ)_/¯')

        ctx.voice_state.songs.shuffle() # random.shuffle() moment :)
        await ctx.message.add_reaction('✅')
    
    @commands.command(name="sshuffle")
    async def _sshuffle(self, ctx: commands.Context):
        """Shuffles the queue everytimes the song ended.
        """
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('I need more tracks to enable this feature!')

        # switch it, nothing more, nothing less.
        ctx.voice_state.super_shuffle = not ctx.voice_state.super_shuffle
        await ctx.send(
            f"Turn **{'on' if ctx.voice_state.super_shuffle else 'off'}** super shuffle!"
        )

    @commands.command(name='removes')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a track from the queue at a given index.
        """
        songs = len(ctx.voice_state.songs)
        if songs == 0:
            return await ctx.send('Empty queue. ¯\_(ツ)_/¯')
        elif songs < index:
            return await ctx.send(f"Index out of range! I only have {songs} tracks in queue!")
        
        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.

        Invoke this command again to unloop the song.
        """
        if ctx.voice_state.loop == Loop.NONE:
            ctx.voice_state.loop = Loop.SINGLE
            await ctx.send(":repeat_one: Now Looping **Current Song**!")
        elif ctx.voice_state.loop ==  Loop.SINGLE:
            ctx.voice_state.loop = Loop.QUEUE
            await ctx.send(":repeat: Now Looping **Queue**!")
        else:
            ctx.voice_state.loop = Loop.NONE
            await ctx.send(":arrow_forward: Disable looping!")
    
    @commands.command(name='loopqueue', aliases=['loopq', 'lq'])
    async def _loopq(self, ctx: commands.Context):
        """Loops the entire queue.

        Invoke this command again to unloop the queue.
        """
        if ctx.voice_state.loop == Loop.SINGLE or ctx.voice_state.loop == Loop.NONE:
            ctx.voice_state.loop = Loop.QUEUE
            await ctx.send(":repeat: Now Looping **Queue**!")
        else:
            ctx.voice_state.loop = Loop.NONE
            await ctx.send(":arrow_forward: Disable looping!")
    
    @commands.command(name="recommend", aliases=['rec'])
    async def _recommend(self, ctx: commands.Context, *, name: str = None):
        """Find a recommendation based on song name or currently playing.
        
        This will find 20 more songs similar songs and add it to the queue.
        You can also use the song url from spotify to search.
        Note: This command use Spotify Recommendation system.
        """
        # name is define, recommend base on it
        if name is not None and ctx.voice_state.audio_player is not None:
            log.info(f"{ctx.guild.id}: Recommending song based on {name}")
            try:
                songs = getRecommend( name.split() )
            except NameError: # couldn't find any match
                log.info(f"{ctx.guild.id}: Unable to find any matched")
                return await ctx.send(":x: **Unable to find matched song.**")
            except SpotifyException as e:
                log.info(f"{ctx.guild.id}: Request fail, {e}")
                return await ctx.send(":x: **Request fail, Try using Spotify URL.**")

            amount = 0
            for s in songs: # load the song
                pl = PlaylistSong(s, ctx)
                await ctx.voice_state.songs.put(pl)
                amount += 1
            
            log.info(f"{ctx.guild.id}: Queued songs.")
            return await ctx.send("Enqueued {} songs.".format(amount))
        # name is not define, but there is a song playing...
        # Note: this works 1% of the time, so good luck.
        elif name is None and ctx.voice_state.current is not None:
            log.info(f"{ctx.guild.id}: Recommending song based on current song...")

            try:
                name = ctx.voice_state.current.source.title
            except AttributeError: 
                return await ctx.send(":x: **Unable to fetch song name, Please try again later.**")
            
            try:
                songs = getRecommend( [name] )
            except NameError:
                log.info(f"{ctx.guild.id}: Unable to find any matched")
                return await ctx.send(":x: **Unable to find matched song, Please try typing it directly.**\n(Spotify URL or Song name)")
            except SpotifyException as e:
                log.info(f"{ctx.guild.id}: Request fail, {e}")
                return await ctx.send(":x: **Request fail, Try using Spotify URL.**")

            amount = 0
            for s in songs: # load the song
                pl = PlaylistSong(s, ctx)
                await ctx.voice_state.songs.put(pl)
                amount += 1
            
            log.info(f"{ctx.guild.id}: Queued songs.")
            return await ctx.send("Enqueued {} songs.".format(amount))
        else:
            # The reason that play command need to be ran before using it because
            # the Audio player will only be run only if play command has been ran
            # so If we tried to put a song in the queue, the song wouldn't actually be play.
            # It's a good thing because we can test if the audio player is running to check 
            # the commands that need a song being play.
            return await ctx.send(":x: **Please use play command before using this command.**")


    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str = None):
        """Plays a song.

        If there are songs in the queue, this will be queued until the
        other songs finished playing.

        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """
        if not ctx.voice_state.voice:
            # not connected? try to join first
            try:
                await ctx.invoke(self._join)             
            except Exception:
                return await ctx.send("Couldn't connect to the voice, Please disconnect me and try again!")
        
        if search is None: # resume
            log.debug(f"{ctx.guild.id}: Resume")
            return await ctx.invoke(self._resume)

        # Remove <> in the url, because some people want to hide the embed.
        search = search.lstrip("<").rstrip(">")
        log.debug(f"{ctx.guild.id}: Searching {search}")
        await ctx.trigger_typing()       

        # Youtube Playlist, Mix        
        if any(kw in search for kw in YOUTUBE_PLAYLIST_KEYWORDS): 
            try: # some source of insanity...
                results = getYtPlaylist(search)
            except Exception:
                return await ctx.send(":x: PlayList not found (Youtube Mix?) or There is a problem with the bot!")    

            amount = 0
            for s, t in zip(results[0], results[1]):
                pl = PlaylistSong(s, ctx, t)
                await ctx.voice_state.songs.put(pl)
                amount += 1            
            await ctx.send("Enqueued {} songs.".format(amount))
        
        # Spotify Playlist
        elif "open.spotify.com/playlist/" in search:
            try: # somewhere in utils.audio
                tracks = getTracks(search)
            except Exception:
                log.warning(traceback.format_exc())
                return await ctx.send(":x: **Failed to load Spotify Plalist!**")
            
            amount = 0
            for s in tracks:                    
                pl = PlaylistSong(s, ctx)
                await ctx.voice_state.songs.put(pl)
                amount += 1            
            await ctx.send("Enqueued {} songs.".format(amount))   

        elif "open.spotify.com/album/" in search: # Spotify Album
            try: # somewhere in utils.audio
                tracks = getAlbum(search)
            except Exception:
                log.warning(traceback.format_exc())
                return await ctx.send(":x: **Failed to load Spotify Album!**")
            
            amount = 0
            for s in tracks: # put in dataclass and queue               
                pl = PlaylistSong(s, ctx)
                await ctx.voice_state.songs.put(pl)
                amount += 1            
            await ctx.send("Enqueued {} songs.".format(amount))   

        elif "open.spotify.com/" in search: # Anything else related to Spotify
            return await ctx.send("Sorry, Only Spotify playlist & Album is support at the moment!") 

        else: # Normal searching. 
            try:
                source = await YTDLSource.create_source(ctx, search)
            except YTDLError as e:
                return await ctx.send(':x: **{}**'.format(str(e)))
            except DownloadError:
                # maybe it's geo restricted, so retry again but this time put "lyric" behind.                
                await ctx.send(f":x: **Could not download that video, Retrying...**")
                await ctx.trigger_typing() 

                try:
                    source = await YTDLSource.create_source(ctx, search + " lyric")
                except (DownloadError, YTDLError):
                    # Idk anymore...
                    self.play_error(ctx.guild.id)
                    if self.errors_count.get(ctx.guild.id, 0) >= 2:
                        log.warning(f"Download problem detected, Couldn't play video in server {ctx.guild.id}")
                        return await ctx.send("Download problem detected, Youtube service may be down... Please try again in a few hours.")
                    return await ctx.send(":x: **Download fail, Please try using an url.**")
            
            song = Song(source)
            await ctx.voice_state.songs.put(song)
            await ctx.send('Enqueued {}'.format(str(source)))
        
        ctx.voice_state.start_player()
        log.debug(f"Enqueued")
    
    @commands.command(name="playnext", aliases=['pn', ])
    async def _play_next(self, ctx: commands.Context, *, search: str) -> None:
        """Play track after current song ended.
        Only work with Youtube video!
        """
        if ctx.voice_state.audio_player is None:
            return await ctx.send("Nothing is being played...!") 
        
        # Remove <> in the url, because some people want to hide the embed.
        search = search.lstrip("<").rstrip(">")        
        log.debug(f"{ctx.guild.id}: Playnext, Searching {search}")
        await ctx.trigger_typing() 

        # Youtube Playlist
        if "youtube.com/playlist?" in search or "&start_radio" in search: 
            return await ctx.send("This command only work with normal searching or Youtube URL!")       
        elif "open.spotify.com/" in search: # Spotify
            return await ctx.send("This command only work with normal searching or Youtube URL.") 
        else: # Normal searching.
            try:
                source = await YTDLSource.create_source(ctx, search)
            except YTDLError as e:
                return await ctx.send(':x: **{}**'.format(str(e)))
            except DownloadError:
                # maybe it's geo restricted, so retry again but this time put "lyric" behind.                
                await ctx.send(f":x: **Could not download that video, Retrying...**")
                await ctx.trigger_typing() 

                try:
                    source = await YTDLSource.create_source(ctx, search + " lyric")
                except (DownloadError, YTDLError):
                    # Idk anymore...
                    self.play_error(ctx.guild.id)
                    if self.errors_count.get(ctx.guild.id, 0) >= 2:
                        log.warning(f"Download problem detected, Couldn't play video in server {ctx.guild.id}")
                        return await ctx.send("Download problem detected, Youtube service may be down... Please try again in a few hours.")
                    return await ctx.send(":x: **Download fail, Please try using an url.**")            
            song = Song(source)

            # Like how skipto works, I will manipulate this list directly at its core.
            ctx.voice_state.songs._queue.appendleft(song)
            await ctx.send('Enqueued {}'.format(str(source)))        
        log.debug(f"Enqueued play next")

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        # make sure user is in vc.
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')


def setup(bot):
    bot.add_cog(Music(bot))