import discord
from discord.ext import commands

from bot import Bot
from utils.reminderManager import DAYS_ENUM, Day, DAYS

DAY_MAP = {
    "m": Day.MONDAY,
    "tu": Day.TUESDAY,
    "w": Day.WEDNESDAY,
    "th": Day.THURSDAY,
    "f": Day.FRIDAY,
    "sa": Day.SATURDAY,
    "su": Day.SUNDAY
}

class DayConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> Day:
        arg = arg.lower()
        index = ctx.message.created_at.weekday() 

        if not arg:
            return DAYS_ENUM[index]

        for i in DAY_MAP:
            if arg.startswith(i):
                return DAY_MAP[i]
        
        try:
            arg = int(arg)
        except ValueError:
            return DAYS_ENUM[index]
        
        try:
            return DAYS_ENUM[arg]
        except IndexError:
            return DAYS_ENUM[index]

class Reminder(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
    
    # radd
    @commands.command(name = "radd")
    async def _radd(self, ctx: commands.Context, day: DayConverter, *, reminder: str) -> None:
        pass
    # rlist
    # rremove

def setup(bot: Bot) -> None:
    bot.add_cog(Reminder(bot))