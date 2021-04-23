# A Day detection system.
# Made by Tpmonkey

from discord.ext.commands import Cog
from discord.ext import tasks

from bot import Bot
from constant import today

class DayLoop(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.today = None
        self.loop.start()

    def cog_unload(self) -> None:
        self.loop.stop()        
    
    @tasks.loop(minutes=1)
    async def loop(self) -> None:
        if self.today is None:  self.today = await self.bot.database.load("TODAY")
        _today = today()

        # Check if the date same as in database.
        if _today != self.today:
            await self.new_day()
        
            await self.bot.database.dump("TODAY", _today)
            self.today = _today
    
    async def new_day(self) -> None:
        """Nothing here"""
        await self.bot.log(__name__, "New day detected.")        
        await self.update_passed()        
    
    async def update_passed(self) -> None:
        """Update passed works, Will be run daily."""
        data = await self.bot.planner.loop_thro()
        for guild_id in data:
            # Check if channels valid or not.
            if not self.bot.manager.check(guild_id):
                continue 
            
            channels = self.bot.manager.get(guild_id)
            channel = self.bot.get_channel(channels['passed'])
            
            for key in data[guild_id]:
                # Note: This will not directly delete old embed, but will let active-works delete it instead.
                embed = self.bot.get_embed(**data[guild_id][key])

                if channel is None: continue
                await channel.send(embed=embed)
    

def setup(bot: Bot) -> None:
    bot.add_cog(DayLoop(bot))