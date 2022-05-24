"""
Bot Setup, Fix Command.
Made by Tpmonkey
"""

from discord.ext.commands import (
    Cog, Context, command, guild_only, has_permissions, cooldown, BucketType
)
from discord import PermissionOverwrite, Forbidden

from bot import Bot

class SetUp(Cog):
    """
    Setup the bot for assignment system!

    If you got a problem, try using `,fix` command.
    still not fixed? direct message the bot!
    """
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def create_channels(self, ctx: Context, info: list) -> None:
        overwrites = { ctx.guild.default_role: PermissionOverwrite(send_messages=False) }
        for name, type_ in info:
            ch = await ctx.guild.create_text_channel(name, overwrites = overwrites)
            self.bot.manager.set(ctx.guild.id, type_, ch.id)
        
    @command()
    @guild_only()
    @cooldown(1, 10, BucketType.guild)
    @has_permissions(manage_guild=True)
    async def setup(self, ctx: Context) -> None:
        """Setup the bot in one command."""
        if str(ctx.guild.id) in self.bot.manager.get_all():
            return await ctx.send(f":x: **You've already setup the bot!**\nYou can type `{ctx.prefix}fix` to fix simple problem!")            
        
        info = [ ("Active-Works", "active"), ("Passed-Works", "passed") ]

        try: 
            await self.create_channels(ctx, info)
        except Forbidden:
            return await ctx.send(":x: **Unable to create channel, Manage Channels Perm required.**")
            
        await self.bot.log(__name__, f'Successfully setup bot in {ctx.guild.id}')
        await ctx.send(":white_check_mark: Successfully setup the bot!")
    
    @command()
    @cooldown(1, 60, BucketType.guild)
    @has_permissions(manage_guild=True)
    async def fix(self, ctx: Context) -> None:
        """Fix channels not working."""
        channels = self.bot.manager.get(ctx.guild.id)
        fix = False

        if len(channels) == 0:
            return await ctx.send(f"Please use `{ctx.prefix}setup` to setup the bot first.")
        
        if not self.bot.manager.check(ctx.guild.id): 
            info = []

            try: 
                channel = channels['active']
            except IndexError: 
                info.append(("Active-Works", 'active'))
            else:
                if self.bot.get_channel(channel) is None: 
                    info.append(("Active-Works", 'active'))
            
            try: 
                channel = channels['passed']
            except IndexError: 
                info.append(("Passed-Works", 'passed'))
            else:
                if self.bot.get_channel(channel) is None: 
                    info.append(("Passed-Works", 'passed'))
                
            await self.create_channels(ctx, info)
            fix = True
        
        await self.bot.log(__name__, 
            f"Command `,setup` has been ran on {ctx.guild.id}, maybe something went wrong... \n"
            f"\nFix has returned `{fix}`")
        await ctx.send(":white_check_mark: **Fix Completed.**\nStill have a problem? Dm me!")


def setup(bot: Bot) -> None:
    bot.add_cog(SetUp(bot))