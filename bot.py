# discord.ext.commands.Bot custom Subclass 
# Made by Tpmonkey

import asyncio
import logging
import traceback
import datetime

import discord
from discord.ext import commands

from constant import Database, today_th
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
        self.log_channel = None
        self.config = config
        self.start_time = datetime.datetime.utcnow()

        log.info("Bot Subclass Created.")

    @classmethod
    def create(cls) -> "Bot":
        # Create bot Instance and return

        loop = asyncio.get_event_loop()
        intents = discord.Intents().all()

        return cls(
            loop= loop,
            command_prefix= config.prefix,
            activity= discord.Game(name= "and Dying"),
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
            try:
                self.load_extension(extension)
            except Exception as e:
                log.warning(f"Couldn't load {extension} with an error: {e}")                

    def add_cog(self, cog: commands.Cog) -> None:
        # just for Logging
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")
    
    async def on_ready(self) -> None:
        log.info("Connected successfully")

    async def on_message(self, message: discord.Message) -> None:
        if not message.author.bot:
            await self.process_commands(message)
    
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not before.author.bot and before.content != after.content:
            await self.process_commands(after)
    
    async def log(self, name: str, message: str, mention: bool = False) -> None:
        await self.wait_until_ready()
        while self.log_channel is None:
            log.info("Attemping to connect to log channel.")
            self.log_channel = self.get_channel(config.log_channel_id)
            await asyncio.sleep(5)
        
        mention = f"<@{self.owner_id}>\n" if mention else ""
        text = f"[{today_th(True)}] | [{name}]: "+ mention + message
        try:
            await self.log_channel.send(text)
        except:
            log.error(f"Unable to log a message with error\n{traceback.format_exc()}")

            while 1:
                try:
                    await self.log_channel.send(
                        f"[{today_th(True)}] | [Bot] " + f"Unable to log a message with error\n{traceback.format_exc()}"
                    )
                    await self.log_channel.send(
                        f"[{today_th(True)}] | [Bot] "+"Log Channel connection is back up"
                    )
                    
                    await self.log_channel.send(text)
                except:
                    # Retrying
                    log.info("Retrying to send a log message in 60.00 seconds")
                    await asyncio.sleep(60.00)
                else:
                    break
    
    async def find_message(self, message_id: int, channel_id: int, limit:int=100) -> discord.Message:
        await self.wait_until_ready()

        channel = self.get_channel(channel_id)

        if not channel:
            channel = self.get_user(channel_id)
            if not channel:
                raise ValueError("Couldn't find TextChannel/User")

        message = None
        async for mess in channel.history(limit=limit):
            if mess.id == message_id:
                message = mess
                break
        
        if not message:
            raise ValueError("Couldn't find that requested Message")
        return message
    
    def to_number(self, number: int) -> str:
        return format(number, ",")
    
    async def wait_for_message(self, ctx: commands.Context, timeout: int = None) -> discord.Message:
        
        def check(m) -> bool:
            return m.channel == ctx.message.channel and m.author.id == ctx.author.id
        
        message = await self.wait_for("message", check=check, timeout=timeout)
        return message

    async def add_reactions(self, message: discord.Message, reactions: list) -> None:
        for reaction in reactions:
            try:
                await message.add_reaction(reaction)
            except:
                pass
    
    async def get_image_url(self, image: discord.Attachment) -> str:
        await image.save(open("evals/image.jpg", "wb"))
        channel = self.get_channel(config.image_channel_id)
        
        image = await channel.send(file=discord.File(open("evals/image.jpg", "rb")))

        image = image.attachments[0].url
        return image