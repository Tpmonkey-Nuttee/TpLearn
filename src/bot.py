"""
TpLearn [BETA] Bot core.
Made by Tpmonkey
"""

import os
import sys
import random
import asyncio
import logging
import datetime
import traceback
from typing import Any
from PIL import Image
from aiohttp import ClientSession

import discord
from discord.ext import commands

import config
from db import Database
from utils.time import today_th
from utils import planner, manager

log = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    "timeout": 300,
    "annouce_next_song": False,
    "vote_skip": True
}

DEFAULT_ACCEPTED_VALUE = {
    "timeout": int,
    "annouce_next_song": bool,
    "vote_skip": bool
}

def get_prefix(bot: commands.Bot, message: discord.Message) -> str:
    # For supporting custom prefix (soon)
    return bot.config.prefix

class Settings:
    def __init__(self, bot):
        self._bot = bot
        self._settings = bot.database.loads("MUSIC", {})

    def __getitem__(self, item):
        return self._settings.get(item, DEFAULT_SETTINGS)
    
    def __iter__(self):
        return self._settings.__iter__()
    
    def get(self, gid, sett):
        """Get guild setting.
        """
        gid = str(gid)

        if gid not in self._settings:
            self._settings[gid] = DEFAULT_SETTINGS
        
        return self._settings[gid][sett]
    
    def set(self, guild_id: int, setting: str, value: Any) -> None:
        """Set guild setting.
        """
        guild_id = str(guild_id)

        value = DEFAULT_ACCEPTED_VALUE[setting](value)

        if guild_id not in self._settings:
            self._settings[guild_id] = DEFAULT_SETTINGS

        self._settings[guild_id][setting] = value

        self._bot.database.dumps("MUSIC", self._settings)
    
    def delete(self, guild_id: int) -> None:
        """Delete guild settings
        """
        try:
            del self._settings[str(guild_id)]
            self._bot.database.dumps("MUSIC", self._settings)
        except KeyError:
            pass


class Bot(commands.AutoShardedBot):
    # Subclass of commands.Bot
    def __init__(self, command_prefix, help_command = None, description = None, **options):
        """ Overwrite Defualt __init__ """
        # Set default Help command
        if not help_command:
            help_command = commands.DefaultHelpCommand()

        super().__init__(command_prefix, help_command, description, **options)

        self.start_time = datetime.datetime.utcnow()
        self.trust_session = ClientSession()     

        # Define database here so It's easier to be use.
        self.database = Database()
        self.msettings = Settings(self)
        self.planner = planner.Planner(self)
        self.manager = manager.Manager(self)
        
        self.config = config

        self.unloaded_cogs = []
        self.last_check = {}

        self.log_channel = None
        self.dump_channel = None
        self.image_channel = None

        log.debug("bot subclass Created.")

    @classmethod
    def create(cls) -> "Bot":
        """ Create bot Instance and return. """

        loop = asyncio.get_event_loop()
        intents = discord.Intents().all()
        log.debug("created bot base.")

        return cls(
            loop = loop,
            command_prefix = get_prefix,
            activity = discord.Activity(type = discord.ActivityType.watching, name = "myself starting..."),
            status = discord.Status.dnd,
            case_insensitive = True,
            max_messages = 10_000,
            intents = intents
        )

    def load_extensions(self) -> None:
        """ Load bot extensions. """
        from utils.extensions import EXTENSIONS
        extensions = set(EXTENSIONS)

        for extension in extensions:
            try: 
                self.load_extension(extension)
            except (commands.ExtensionFailed, commands.NoEntryPointError) as e: 
                log.warning(f"Couldn't load {extension} with an error: {e}")   
                self.unloaded_cogs.append(extension)             

    def add_cog(self, cog: commands.Cog) -> None:
        """ Add Cog event, Need for logging. """
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")
    
    @property
    def uptime(self):
        """ Bot Uptime Property, Can be acces using Admin Command only. """
        return datetime.datetime.now() - self.start_time
    
    def get_random_status(self) -> discord.Activity:
        """ Get random Bot statuses. """
        c = self.planner.get_number_all()

        # Calculate round users count.
        users = (len(self.users) // 10) * 10

        statuses = (
            discord.Activity(type = discord.ActivityType.watching, name = f"~{format(users, ',')} users"),
            discord.Activity(type = discord.ActivityType.watching, name = f"{c} assignments"),
            discord.Activity(type = discord.ActivityType.playing, name = f"in {len(self.guilds)} servers"), 
            discord.Activity(type = discord.ActivityType.playing, name = ",help command"),           
            discord.Activity(type = discord.ActivityType.playing, name = "with python")
        )
        return random.choice(statuses)
    
    def unload_cogs(self) -> None:
        """Unload all extension."""
        extensions = [ext for ext in self.extensions]
        # haha, RuntimeError again!
        for extension in extensions:
            if extension == "exts.admin": 
                # Ignore admin cog.
                continue

            try:
                self.unload_extension(extension)
            except (commands.ExtensionNotLoaded, commands.ExtensionNotFound):
                pass
    
    async def close(self) -> None:
        await super().close()

        await self.trust_session.close()
        sys.exit(69)
    
    async def on_ready(self) -> None:
        """ on Ready event, Use to log and change bot status. """
        log.info("Connected successfully")
        # await self.log(__name__, "connected")
        await self.change_status()
        
        if self.unloaded_cogs:
            text = "".join([f"Unable to load **{cog}**\n" for cog in self.unloaded_cogs])
            await self.log(__name__, text, True)
    
    async def on_resumed(self) -> None:
        """ on Edit event, Use to log and change bot status. """
        log.info("Resumed Connection")
        # await self.log(__name__, "resumed connection")
        await self.change_status()
    
    async def change_status(self) -> None:
        """ Change bot status, randomly from get_random_status method. """    
        await self.change_presence(activity = self.get_random_status())
        log.debug("changed bot status")

    async def on_message(self, message: discord.Message) -> None:
        """ on Message event. """
        # Bot will only response to normal user only, not another bot.
        if not message.author.bot: 
            await self.process_commands(message)
    
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """ on Message Edit event. """
        # If message were edited, and content changed. Re-process command.
        if not before.author.bot and before.content != after.content: 
            await self.process_commands(after)
    
    async def on_error(self, event_method, *args, **kwargs) -> None:
        """ on Error event, Use to log in discord channel so can be easily look back. """
        log.error(traceback.format_exc())

        await self.wait_until_ready()
        if self.dump_channel is None: 
            self.dump_channel = self.get_channel(config.dump_channel_id)
        
        embed = discord.Embed( timestamp = datetime.datetime.utcnow())
        embed.add_field(name = "Event Method", value = str(event_method), inline = False)
        embed.add_field(name = "Args", value = str(args), inline = False)
        embed.add_field(name = "Kwargs", value = str(kwargs), inline = False)

        message = traceback.format_exc().replace('```', '\```')

        try: 
            await self.dump_channel.send(content = f"```py\n{message}\n```", embed = embed)
        except discord.HTTPException:
            try:
                await self.dump_channel.send(
                    "<@!518063131096907813> Unhandle error occured, Please check the bot logs.\n"
                    f"error with `{len(message)}` letters long."
                )
            except discord.HTTPException: 
                pass
    
    async def log(self, name: str, message: str = "", mention: bool = False, embed: discord.Embed = None) -> None:
        """
        Log Message to Bot's log-channel.
        """
        log.info(f"{name} {message}")
        await self.wait_until_ready()

        while self.log_channel is None: 
            self.log_channel = self.get_channel(config.log_channel_id)
        
        mention = f"<@!{self.owner_id}>\n" if mention else "\n"
        text = f"**[{today_th(True)}] | [{name}]:** {mention} {message}"

        if len(text) > 1024:
            text = text[:1020] + "..."

        try: 
            await self.log_channel.send(text, embed=embed)
        except discord.HTTPException:
            log.error(f"unable to log a message with error:\n{traceback.format_exc()}")
        else: 
            return
    
    async def wait_for_message(self, ctx: commands.Context, timeout: int = None) -> discord.Message:
        """
        Wait for User message, Time Limit is optional.
        
        Checks:
        - Message is the same channel as ran command.
        - Author needs to be the person who ran command.
        """    
        def check(m) -> bool: 
            return m.channel == ctx.channel and m.author == ctx.author   

        log.debug("waiting for message...")        
        return await self.wait_for("message", check=check, timeout = timeout)

    async def add_reactions(self, message: discord.Message, reactions: list) -> None:
        """ Add Set/List of Reactions to targeted message. """
        for reaction in reactions:
            try: 
                await message.add_reaction(reaction)
            except (discord.HTTPException, discord.Forbidden) as e:
                log.debug(f"could not add {reaction} reaction with exception: {e}")
    
    async def get_image_from_gif(self, gif_url: str) -> str:
        """Returns first frame of gif in url

        Args:
            gif_url (str): GIF url

        Returns:
            str: Image url
        """
        if self.image_channel is None:
            self.image_channel = self.get_channel(config.image_channel_id)
        
        r = await self.trust_session.get(gif_url)

        with open("evals/gif.gif", "wb") as f:
            # Save gif into file.
            byte = await r.content.read()
            f.write(byte)
            f.close()
        
        # Save first frame into png.
        im = Image.open("evals/gif.gif")
        im.seek(0) # First frame.
        im.save("evals/gif.png")

        message = await self.image_channel.send(
            file = discord.File("evals/gif.png")
        ) 
        # Will override the old one everytime, No need to delete.
        return message.attachments[0].url    
    
    async def get_image_url(self, image: discord.Attachment) -> str:
        """ 
        Get Image URL from discord.Attachment or discord.File object.
        """
        if self.image_channel is None:
            self.image_channel = self.get_channel(config.image_channel_id)


        # Save the image, turn it into a File object.
        await image.save(open("evals/image.jpg", "wb"))
        image = discord.File("evals/image.jpg")

        # Sent it to image-placeholder channel then get the url.
        image = await self.image_channel.send(file=image)
        image = image.attachments[0].url

        # Delete it.
        os.remove("evals/image.jpg")
        log.debug("got Image, return and deleted.")
        return image
    
    def in_days(self, date1: str, date2: str = None) -> int:
        """ Return amount of days between today and targeted date. """
        if date2 is None:
            date2 = today_th()
        strpped = self.planner.try_strp_date(date1)
        
        return None if strpped is None else (strpped - datetime.datetime.strptime(date2, "%Y-%m-%d")).days
    
    def get_colour(self, date: str = "", gap: int = None, passed: bool = False, lasted: int = 1) -> discord.Colour:
        """
        Get Embed Colour base on Deathline of assignment.

        Colours List
        * purple - unknown date format, invalid date, no limit time.
        * teal - has time for more or equal to 2 weeks.
        * dark_teal - has time for more or equal to 1 week.
        * gold - has time for more or equal to 4 days.
        * dark_gold - has time for more or equal to 2 days.
        * dark_orange - has time for 1 day, or need to send tomorrow.
        * dark_red - needs to send today.
        * default (black) - already passed.        
        """
        if passed: 
            return discord.Colour.default()
        if gap is None: 
            gap = self.in_days(date)

        if gap is None: 
            return discord.Colour.purple()
        if gap >= 14: 
            return discord.Colour.teal()
        if gap >= 7: 
            return discord.Colour.dark_teal()
        if gap >= 4: 
            return discord.Colour.gold()
        if gap >= 2: 
            return discord.Colour.dark_gold()
        if gap == 1: 
            return discord.Colour.dark_orange()
        if gap <= 0: 
            if lasted == 1 or lasted + gap >= 0:
                return discord.Colour.dark_red()
        return discord.Colour.default()
    
    def get_title(self, title: str, date: str, passed: bool = False, lasted: int = 1) -> str:
        """ Get Embed Title. """
        if passed: 
            return title + " [ PASSED ]"

        in_day = self.in_days(date)
        
        if in_day is None: 
            in_day = ""
        elif in_day > 1:
            if lasted == 1:
                in_day = f" [In {in_day} days]"
            else:
                in_day = f" [Starts in {in_day} days]"
        elif in_day == 1: 
            if lasted == 1:
                in_day = " [❗❗ TOMORROW ❗❗]"
            else:
                in_day = f" [❗❗ STARTING TOMORROW ❗❗]"
        elif in_day <= 0: 
            if in_day == 0 and lasted == 1:
                in_day = " [❗❗ TODAY ❗❗]"
            elif in_day < 0 and lasted == 1:
                in_day = " [ PASSED ]"
            else:
                in_day = f" [ Ends in {abs(in_day + lasted)} days ]"
        else: 
            in_day = f" [In {in_day} days]"

        return title + in_day
    
    def get_embed(self, **kwargs) -> discord.Embed:
        """ 
        Get Assignment Embed, base on Information provided.

        Required kwargs:
        * title: str - Assignment Title
        * key: str - Assignment Key
        * date: str - Assignment send date
        * readable-date: str - Readable date, can be the same as date
        * desc: str - Assignment Description
        * image-url: str - Image URL. Set it to 'Not Attached' to disable.
        """
        log.debug("creating assignment embed...")
        title = self.get_title(kwargs.get('title'), kwargs.get('date'), passed=kwargs.get("already_passed"), lasted=kwargs.get("lasted", 1))
        
        embed = discord.Embed(timestamp = datetime.datetime.now())
        embed.set_author(name = title)
        embed.description = kwargs.get('key')
        embed.colour = self.get_colour(kwargs.get('date'), passed = kwargs.get("already_passed"), lasted=kwargs.get("lasted", 1))    
        
        # Date
        readable_date = kwargs.get('readable-date')
        lasted = kwargs.get("lasted", 1)

        if lasted == 1:
            value = readable_date
        else:
            value = f"Starts at **{readable_date}** and lasts for **{lasted}** day{'s' if lasted > 1 else ''}."

        embed.add_field(
            name = ":calendar_spiral: Date: ", 
            value = value, 
            inline = False
        )

        desc = kwargs.get('desc')
        if desc != "No Description Provided":
            embed.add_field(name = ":clipboard: Description: ", value = desc, inline = False)

        embed.set_footer(text = f"Key: {kwargs.get('key')}")

        if kwargs.get('image-url') != "Not Attached": 
            embed.set_image(url=kwargs.get('image-url'))
        
        log.debug("successfully created assignment embed")
        return embed
    
    async def update(self, ctx: commands.Context, url: str = None) -> None:
        """Update itself from github"""
        from updater.update import update
        
        if url is None:
            url = "https://github.com/Tpmonkey-Nuttee/TpLearn/archive/refs/heads/master.zip"
        
        await update(url, os.getcwd(), ctx)
    
    def restart(path: str) -> None:
        log.info("Restarting process")

        args = sys.argv[:]
        args.insert(0, sys.executable)

        os.execv(sys.executable, args)