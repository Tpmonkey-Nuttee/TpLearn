"""
Bot Ping Display, and Socket Session command for Admin
Made by Tpmonkey
"""

from discord import Embed, Color, utils
from discord.ext.commands import command, Cog, Context, is_owner

from bot import Bot

from datetime import datetime
from collections import Counter
from utils.time import StatsInTime

DESCRIPTION = (
    "Discord API latency",
    "Command processing time"
)

class Latency(Cog):
    """Display ping!"""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.socket_since = datetime.utcnow()
        self.socket_event_total = 0
        self.socket_events = Counter()
        self.in_time = StatsInTime(limit = 10_000)
    
    @Cog.listener()
    async def on_socket_response(self, msg: dict) -> None:
        if event_type := msg.get("t"):
            self.socket_event_total += 1
            self.socket_events[event_type] += 1
            self.in_time.append("0")
    
    @command()
    async def ping(self, ctx: Context) -> None:
        """Display API ping and Command Process time."""
        discord_ping = f"{ (self.bot.latency*1000):.{3}f} ms"

        bot_ping = (utils.utcnow() - ctx.message.created_at).total_seconds() * 1000
        bot_ping = f"{bot_ping:.{3}f} ms"

        embed = Embed(
            title = "Pong!",
            color = Color.magenta()
        )
        
        for des, val in zip(DESCRIPTION, [discord_ping, bot_ping]):
            embed.add_field(name = des, value = val, inline = False)

        await ctx.send(embed=embed)
    
    @is_owner()
    @command(aliases = ("ss", ))
    async def socketstats(self, ctx: Context) -> None:
        """Fetch information on the socket events received from Discord."""
        running_s = (datetime.utcnow() - self.socket_since).total_seconds()

        per_s = self.socket_event_total / running_s
        per_t = self.in_time.get_in_last(3600) / 3600

        stats_embed = Embed(
            title = "WebSocket statistics",
            description = f"Receiving {per_s:0.2f} event per second.\nReceiving {per_t:0.2f} event in the last hour.\n ",
            color = Color.blurple(),
            timestamp = self.bot.start_time
        )

        for event_type, count in self.socket_events.most_common(25):
            stats_embed.add_field(name=event_type, value=count, inline=False)

        await ctx.send(embed=stats_embed)

    @command(hidden=True)
    async def pong(self, ctx: Context) -> None:
        await ctx.send("You meant... ping right...?")

async def setup(bot: Bot) -> None:
    await bot.add_cog(Latency(bot))