from discord.ext.commands import Cog
from discord.ext import tasks

from bot import Bot
from constant import today

class DayLoop(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.today = today()
        self.loop.start()

    def cog_unload(self) -> None:
        self.loop.stop()
    
    @tasks.loop(minutes= 1)
    async def loop(self) -> None:
        today = await self.bot.database.load("TODAY")

        if today != self.today:
            await self.new_day()
    
    async def new_day(self) -> None:
        new_day = today()

        await self.bot.database.dump("TODAY", new_day)
        self.today = new_day  
    

def setup(bot: Bot) -> None:
    bot.add_cog(DayLoop(bot))