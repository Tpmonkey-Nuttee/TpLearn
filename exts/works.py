from discord.ext.commands import Cog, Context, command, guild_only

from bot import Bot
from utils.planner import get_all

class Planner(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @command()
    @guild_only()
    async def allworks(self, ctx: Context) -> None:
        d = (await get_all(ctx.guild.id)).display
        n = [d[i]['title'] for i in d]
        await ctx.send("\n".join(n))


def setup(bot: Bot) -> None:
    bot.add_cog(Planner(bot))