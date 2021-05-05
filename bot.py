# discord.ext.commands.Bot custom Subclass 
# Made by Tpmonkey

import os
import random
import asyncio
import logging
import datetime
import traceback
from aiohttp import ClientSession

import discord
from discord.ext import commands

from constant import Database, today_th
from utils import planner, manager
import config

log = logging.getLogger(__name__)

class Bot(commands.Bot):
    # Subclass of commands.Bot
    def __init__(self, command_prefix, help_command=None, description=None, **options):
        # Set default Help command
        if not help_command:
            help_command = commands.DefaultHelpCommand()

        super().__init__(command_prefix, help_command, description, **options)

        # Define database here so It's easier to be use.
        self.database = Database()

        self.planner = planner.Planner(self)
        self.manager = manager.Manager(self)
        self.config = config

        self.log_channel = None
        self.dump_channel = None
        
        self.start_time = datetime.datetime.utcnow()
        self.trust_session = ClientSession()       

        log.info("Bot Subclass Created.")

    @classmethod
    def create(cls) -> "Bot":
        # Create bot Instance and return

        loop = asyncio.get_event_loop()
        intents = discord.Intents().all()

        return cls(
            loop= loop,
            command_prefix= config.prefix,
            activity= discord.Activity(type=discord.ActivityType.watching, name="myself starting..."),
            status= discord.Status.dnd,
            case_insensitive= False,
            max_messages= 10_000,
            intents = intents
        )

    def load_extensions(self) -> None:
        # Load all extensions
        from utils.extensions import EXTENSIONS
        extensions = set(EXTENSIONS)

        for extension in extensions:
            try: self.load_extension(extension)
            except Exception as e: log.warning(f"Couldn't load {extension} with an error: {e}")                

    def add_cog(self, cog: commands.Cog) -> None:
        # just for Logging
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")
    
    @property
    def uptime(self):
        return datetime.datetime.now() - self.start_time
    
    def get_random_status(self) -> discord.Activity:
        c = self.planner.get_number_all()

        # Calculate round users count.
        users = len(self.users)
        _power = 10 ** (len(str(users)) - 1)
        users = (users // _power) * _power

        statuses = [
            discord.Activity(type=discord.ActivityType.watching, name=f"{c} assignments"),
            discord.Activity(type=discord.ActivityType.playing, name=f"in {len(self.guilds)} servers"),
            discord.Activity(type=discord.ActivityType.watching, name=f"~{format(users, ',')} users"),
            discord.Activity(type=discord.ActivityType.playing, name="with python"),
            discord.Activity(type=discord.ActivityType.playing, name=",help command")
        ]
        return random.choice(statuses)
    
    async def on_ready(self) -> None:
        log.info("Connected successfully")
        await self.change_status()
    
    async def on_resumed(self) -> None:
        log.info("Resumed Connection")
        await self.change_status()
    
    async def change_status(self) -> None:        
        await self.change_presence(activity = self.get_random_status())

    async def on_message(self, message: discord.Message) -> None:
        if not message.author.bot:await self.process_commands(message)
    
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not before.author.bot and before.content != after.content: await self.process_commands(after)
    
    async def on_error(self, event_method, *args, **kwargs) -> None:
        log.error(traceback.format_exc())

        await self.wait_until_ready()
        if self.dump_channel is None: self.dump_channel = self.get_channel(config.dump_channel_id)
        
        embed = discord.Embed( timestamp = datetime.datetime.utcnow())
        embed.add_field(name="Event Method", value=str(event_method), inline=False)
        embed.add_field(name="Args", value=str(args), inline=False)
        embed.add_field(name="Kwargs", value=str(kwargs), inline=False)
        message = traceback.format_exc().replace('```', '\```')
        try:
            await self.dump_channel.send(
                content = f"```py\n{message}\n```", 
                embed=embed
            )
        except:
            await self.dump_channel.send(
                "<!@518063131096907813> Unhandle error occured, Please check the bot logs." \
                f"error with `{len(message)}` letters long."
            )
    
    async def log(self, name: str, message: str = "", mention: bool = False, embed: discord.Embed = None) -> None:
        await self.wait_until_ready()
        while self.log_channel is None: self.log_channel = self.get_channel(config.log_channel_id)
        
        mention = f"<@{self.owner_id}>\n" if mention else "\n"
        text = f"**[{today_th(True)}] | [{name}]:** "+ mention + message
        try: await self.log_channel.send(text, embed=embed)
        except:
            log.error(f"Unable to log a message with error\n{traceback.format_exc()}")
            rn = today_th(True)
        else: return

        while 1:
            try:
                await self.log_channel.send(
                    f"**[{today_th(True)}] | [Bot] **" + f"<@{self.owner_id}>\n" + \
                    f"Log connection went out for little while. ({rn})" + \
                    f"\n{traceback.format_exc()}"
                )
                
                await self.log_channel.send(text, embed=embed)
            except discord.HTTPException:
                await self.log_channel.send("An Exception is longer than 2000 characters, Please check the log.")
                break
            except: # Retrying                    
                log.info("Retrying to send a log message in 60.00 seconds")
                await asyncio.sleep(60.00)
            else: break
    
    async def wait_for_message(self, ctx: commands.Context, timeout: int = None) -> discord.Message:        
        def check(m) -> bool: return m.channel == ctx.channel and m.author == ctx.author   

        message = await self.wait_for("message", check=check, timeout=timeout)
        return message

    async def add_reactions(self, message: discord.Message, reactions: list) -> None:
        for reaction in reactions:
            try: await message.add_reaction(reaction)
            except: pass
    
    async def get_image_url(self, image: discord.Attachment) -> str:
        # Save the image.
        await image.save(open("evals/image.jpg", "wb"))

        # Sent it to image-placeholder channel then get the url.
        channel = self.get_channel(config.image_channel_id)        
        image = await channel.send(file=discord.File(open("evals/image.jpg", "rb")))
        image = image.attachments[0].url

        # Delete it.
        os.remove("evals/image.jpg")
        return image
    
    def in_days(self, date1: str, date2: str = today_th()) -> int:
        strpped = self.planner.try_strp_date(date1)
        return None if strpped is None else (strpped - datetime.datetime.strptime(today_th(), "%Y-%m-%d")).days
    
    def get_colour(self, date: str) -> discord.Colour:
        gap = self.in_days(date)

        if gap is None: return discord.Colour.purple()
        elif gap >= 14: return discord.Colour.teal()
        elif gap >= 7: return discord.Colour.dark_teal()
        elif gap >= 4: return discord.Colour.gold()
        elif gap >= 2: return discord.Colour.dark_gold()
        elif gap == 1: return discord.Colour.dark_orange()
        elif gap == 0: return discord.Colour.dark_red()
        return discord.Colour.default()
    
    def get_title(self, title: str, date: str) -> str:
        in_day = self.in_days(date)
        if in_day is None: in_day = ""
        elif in_day == 0: in_day = " [❗❗ TODAY ❗❗]"
        elif in_day == 1: in_day = " [❗❗ TOMORROW ❗❗]"
        elif in_day < 0: in_day = " [ PASSED ]"
        else: in_day = f" [In {in_day} days]"

        return title + in_day
    
    def get_embed(self, **kwargs) -> discord.Embed:
        embed = discord.Embed( timestamp = datetime.datetime.now() )
        embed.colour = self.get_colour(kwargs.get('date'))
        embed.description = kwargs.get('key')

        title = self.get_title(kwargs.get('title'), kwargs.get('date'))

        embed.set_author(name = title)
        embed.add_field(name = "Date: ", value= kwargs.get('readable-date'), inline = False)
        embed.add_field(name = "Description: ", value = kwargs.get('desc'), inline = False)
        embed.set_footer(text = f"Key: {kwargs.get('key')}")

        if kwargs.get('image-url') != "Not Attached": embed.set_image(url=kwargs.get('image-url'))
        
        return embed