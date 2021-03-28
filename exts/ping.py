# Ping display
# Made by Tpmonkey

from discord.ext.commands import command, Cog, Context
from discord import Embed, Color

from bot import Bot

from datetime import datetime

description = (
    "Discord API latency",
    "Command processing time"
)

class Latency(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @command(name = "ping")
    async def ping(self, ctx: Context) -> None:
        # Display API ping and Command Process time.
        discord_ping = f"{ (self.bot.latency*1000):.{3}f} ms"

        bot_ping = (ctx.message.created_at - datetime.utcnow()).total_seconds() * 1000
        bot_ping = f"{bot_ping:.{3}f} ms"

        embed = Embed(
            title = "Pong!",
            color = Color.magenta()
        )
        
        for des, val in zip(description, [discord_ping, bot_ping]):
            embed.add_field(name = des, value = val, inline = False)

        await ctx.send(embed=embed)

def setup(bot: Bot) -> None:
    bot.add_cog(Latency(bot))