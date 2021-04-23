from discord.ext.commands import Cog, Context, command

from bot import Bot

class Settings(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


def setup(bot: Bot) -> None:
    bot.add_cog(Settings(bot))