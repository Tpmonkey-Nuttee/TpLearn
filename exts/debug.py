from discord.ext.commands import Cog, Context, command, is_owner, guild_only
from discord import File

from bot import Bot

import json
import logging
import asyncio

log = logging.getLogger(__name__)

class Debug(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
    
    @command(aliases = ("wdebug", "adebug", ), hidden=True)
    @is_owner()
    @guild_only()
    async def work_debug(self, ctx: Context, key: str, guild_id: int = None) -> None:
        if guild_id is None:
            guild_id = ctx.guild.id
        
        try:
            work = dict(self.bot.planner.get(guild_id, key))
        except KeyError:
            await ctx.send(f":x: **KeyError**; Work does not exist in server ({guild_id})")
            return
        except Exception as e:
            await ctx.send(f":x: **Look up error, Something went wrong**; {e}")
            return
        
        json.dump(work, open("evals/work_debug.json", "w"), indent=2)
        await ctx.send(file=File("evals/work_debug.json"))
    
    @command()
    @is_owner()
    async def edit_test(self, ctx: Context, time: float) -> None:
        m = await ctx.send("Hey")
        for i in range(20):
            try:
                await m.edit(content = i)
            except:
                await ctx.send("too often")
                break
            await asyncio.sleep(time)


def setup(bot: Bot) -> None:
    bot.add_cog(Debug(bot))