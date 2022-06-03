"""
A Day detection system, Use to check new day.
Made by Tpmonkey
"""

from discord.ext import tasks
from discord.ext.commands import Cog, Context, command

import config
from bot import Bot
from utils.time import today, today_th

import logging
import traceback

log = logging.getLogger(__name__)

MINUTES = config.check_day_cooldown

class DayLoop(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.today_morning = None
        self.today_th = None
        self.loop.start()

    def cog_unload(self) -> None:
        self.loop.stop()     

    @Cog.listener()
    async def on_resumed(self) -> None:
        """
        Check if loop running correctly.
        """
        if not self.loop.is_running():
            self.loop.restart()
            await self.bot.log(__name__, "DayLoop is not running, Restarted", True)
            await self.bot.log(__name__, traceback.format_exc())                
    
    @tasks.loop(minutes=MINUTES)
    async def loop(self) -> None:
        if self.today_morning is None:  
            self.today_morning = await self.bot.database.load("TODAY")

        if self.today_th is None:  
            self.today_th = await self.bot.database.load("TODAY-TH")
        
        today_new = today()

        # Check if the date same as in database.
        if today_new != self.today_morning:
            await self.newDay()
            await self.bot.database.dump("TODAY", today_new)    

            self.today_morning = today_new
        
        today_th_ = today_th()

        if today_th_ != self.today_th:
            await self.newDay_th()
            await self.bot.database.dump("TODAY-TH", today_th_)

            self.today_th = today_th_

    async def newDay_th(self) -> None:
        """ Trigger Assignment system to update. """
        await self.bot.log(__name__, "New day [UTC+7] detected.")
        self.bot.planner.trigger_update()
    
    async def newDay(self) -> None:
        """ Newday Event. """
        await self.bot.log(__name__, "New day [UTC+1] detected.")
        await self.update_passed()
        await self.delete_passed()  

        self.bot.planner.trigger_update()
    
    async def update_passed(self) -> None:
        """Update passed works, Will be run daily."""
        log.debug('updating passed work')
        data = await self.bot.planner.loop_thro()
        for guild_id in data:
            # Check if channels valid or not.
            log.debug(f'updating {guild_id}')
            if not self.bot.manager.check(guild_id): 
                log.debug('check failed, passing...')
                continue 
            
            channels = self.bot.manager.get(guild_id)
            channel = self.bot.get_channel(channels['passed'])
            
            for key in data[guild_id]:
                # Note: This will not directly delete old embed, but will let active-works delete it instead.
                payload = data[guild_id][key]
                payload["already-passed"] = True
                embed = self.bot.get_embed(**payload)

                if channel is None: 
                    log.debug(f'invalid channel in {guild_id}, passing')
                    continue

                await channel.send(embed=embed)
            
            log.debug(f'updated {guild_id}')
    
    async def delete_passed(self) -> None:
        """
        Delete all passed works that passed maximum days which defined in config.py
        If It could delete, It will log the amount of deleted works.
        """
        amount = await self.bot.planner.delete_old_work()
        if amount != 0:
            await self.bot.log(__name__, f"Deleted passed works with amount: {amount}")

    @command(hidden=True)
    async def today(self, ctx: Context) -> None:
        """;)"""
        await ctx.send(self.today_th)


def setup(bot: Bot) -> None:
    bot.add_cog(DayLoop(bot))