import discord
from discord.ext import commands

from bot import Bot
from utils.reminderManager import DAYS_ENUM, Day, TooManyReminders

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
        
    @commands.command(name = "rtest")
    async def _rtest(self, ctx: commands.Context, day: DayConverter) -> None:
        await ctx.send(day)

    # radd
    @commands.command(name = "radd")
    async def _radd(self, ctx: commands.Context, day: DayConverter, *, reminder: str) -> None:
        try:
            self.bot.reminderManager.add(ctx.author.id, day, reminder)
        except TooManyReminders:
            return await ctx.send("You have reached maximum reminders possible!")
        await ctx.send(f"Added `{reminder}` to {day.value}")
    
    # rlist
    @commands.command(name = "rlist")
    async def _rlist(self, ctx: commands.Context) -> None:
        pass
    
    # rremove
    @commands.command(name = "rremove")
    async def _remove(self, ctx: commands.Context, day: DayConverter, index: int) -> None:
        pass

async def setup(bot: Bot) -> None:
    await bot.add_cog(Reminder(bot)) 