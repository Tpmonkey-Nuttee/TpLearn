"""
Check if the instance dupe or not.
Because bot is running on replit, and sometimes replit dupe the bot instance.
"""

import discord
from discord.ext import tasks
from discord.ext import commands

import json
import asyncio
from datetime import datetime

CHANNEL_ID = 966245810033549342

class DupeCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel = None
        self.messages = []

        self.ping = bot.latency

        self.loop.start()
    
    def cog_unload(self):
        self.loop.cancel()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.id != self.bot.user.id:
            return

        if message.created_at.minute != 0:
            return
        
        if message.channel.id != CHANNEL_ID:
            return
        
        self.messages.append(
            json.loads(message.content)
        )
    
    async def check(self) -> None:
        if len(self.messages) <= 1:
            return # No dupe instance
        
        min_latency = min(self.messages)

        if min_latency == self.ping:
            return await self.bot.log(__name__, f"Instance {self.ping}: I will remain online")
        
        await self.bot.log(__name__, "Dupe instance found, Shutdowning this instance.")
        await self.bot.unload_cogs()
        await self.bot.close()

    @tasks.loop(minutes = 1)
    async def loop(self) -> None:
        rn = datetime.utcnow()

        if rn.minute != 0:
            return
        
        self.messages = []
        self.ping = self.bot.latency

        await self.channel.send(self.ping)
        await asyncio.sleep(60) # Wait to gather all respond.
        await self.check()
    
    @loop.before_loop
    async def before_invoke(self) -> None:
        await self.bot.wait_until_ready()
        self.channel = self.bot.get_channel(CHANNEL_ID)


async def setup(bot: commands.Bot) -> None:
    return
    await bot.add_cog(DupeCheck(bot))