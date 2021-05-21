"""
Utility and Fun Commands.
Made by Tpmonkey
"""

from discord.ext.commands import Cog, Context, command
from discord import Embed, Colour

from bot import Bot

import random

class Utility(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @command(aliases = ('fact', 'tips', 'tip', 'qoute', ))
    async def facts(self, ctx: Context) -> None:
        """Some random facts, tips, qoutes"""
        f = random.choice(self.bot.config.facts)
        if "youtube" in f:
            content = None
            embed = Embed(description = f, colour = Colour.blue())
        else:
            content = f
            embed = None
        await ctx.send(content = content, embed=embed)
    
    @command(aliases = ('update', 'ver', 'patch', ))
    async def version(self, ctx: Context) -> None:
        embed = Embed(
            title = f"Version {self.bot.config.version}",
            colour = Colour.blue(),
            timestamp = ctx.message.created_at
        )
        value = "\n".join(self.bot.config.note) if len(self.bot.config.note) != 0 else "No patch note were found."
        embed.add_field(name="Patch Notes:", value = value)
        await ctx.send(embed=embed)

    @command(hidden=True)
    async def hello(self, ctx: Context) -> None:
        await ctx.send("Hello World!")

def setup(bot: Bot) -> None:
    bot.add_cog(Utility(bot))