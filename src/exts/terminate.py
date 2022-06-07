import discord
from discord.ext import commands 

from bot import Bot

from asyncio import TimeoutError

class Terminate(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
    
    @commands.command(name = "terminate", aliases = ["getout", ])
    @commands.has_permissions(manage_guild = True)
    async def kickme(self, ctx: commands.Context) -> None:
        """Kick the bot & Wipe all data"""
        def check(m: discord.Message) -> bool:
            return m.content == "Confirm" and m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("Type `Confirm` to confirm and wipe all data + kick the bot.")

        try:
            await self.bot.wait_for("message", check=check)
        except TimeoutError:
            return await ctx.send("Time out!")

        self.bot.planner.delete_guild(ctx.guild.id)
        self.bot.manager.delete(ctx.guild.id)
        self.bot.msettings.delete(ctx.guild.id)

        await ctx.send("See you later!")
        await ctx.guild.leave()

def setup(bot: Bot) -> None:
    bot.add_cog(Terminate(bot))