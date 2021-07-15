from discord.ext.commands import Cog, Context, command, is_owner, guild_only
from discord import File, Embed

from bot import Bot

from datetime import datetime
import json
import logging
import asyncio

log = logging.getLogger(__name__)

class Debug(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
    
    @command(hidden=True)
    @guild_only()
    async def debug(self, ctx: Context) -> None:
        embed = Embed(
            title = "Server Debug",
            description = "Hello, Hacker man \:)",
            timestamp = ctx.message.created_at
        )

        # Assignment Data
        valid = len(self.bot.planner.get_all(ctx.guild.id))
        invalid = self.bot.planner.get_number_all_passed(ctx.guild.id)
        embed.add_field(
            name="Assignments",
            value = f"total: {valid+invalid}/{self.bot.config.assignment_limit}+{invalid}"
            f"\nvalid: {valid}\ninvalid: {invalid}",
            inline=False
        )

        # Assignment Channels
        is_valid = self.bot.manager.check(ctx.guild.id)
        embed.add_field(
            name="Channels",
            value = f"valid: {is_valid}",
            inline=False
        )

        # Time
        kus_last = self.bot.last_check.get("kus-news")
        if kus_last is not None: kus_last = datetime.utcnow() - kus_last
        update_last = self.bot.last_check["update"].get(str(ctx.guild.id))
        if update_last is not None: update_last = datetime.utcnow() - update_last
        embed.add_field(
            name="Time",
            value = f"kus-news: {kus_last}/{self.bot.config.kus_news_cooldown}\nupdate: {update_last}/{self.bot.config.update_work_cooldown}",
            inline=False
        )

        embed.set_footer(text=f"ver: {self.bot.config.version}")


        await ctx.send(embed=embed)


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