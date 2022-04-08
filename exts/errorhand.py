"""
Bot's Commands Error Handler.
Idea from Python Discord Bot team on Github.
Credit: https://github.com/python-discord/bot
Re-created By Tpmonkey
"""

from discord.ext import commands
import discord

from bot import Bot

import logging

log = logging.getLogger(__name__)


class ErrorHandler(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot =  bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.errors.CommandError) -> None:
        # Error handler
        command = ctx.message.content[1:]

        # Already Handled
        if hasattr(error, "handled"):
            log.trace(f"Command: {command}; Already handled locally.")
            return               

        if isinstance(error, commands.errors.CommandNotFound):
            return

        if isinstance(error, commands.errors.UserInputError):
            return await self.handle_user_input_error(ctx, error)            
        elif isinstance(error, commands.errors.CheckFailure):
            return await self.handle_check_failure(ctx, error)            
        elif isinstance(error, commands.errors.CommandOnCooldown):
            return await ctx.send(f":x: **{error}**")            
        else:
            try: 
                await ctx.send(":x: **Something went wrong while processing your request!**")        
            except discord.HTTPException: 
                log.warning("couldn't send message.")

        log.debug(            
            f"Command {command} invoked by {ctx.author} with error "
            f"{error.__class__.__name__}: {error}")
        await self.bot.log(__name__,
            f":negative_squared_cross_mark: Command `{command}` invoked by `{ctx.author}` with error \n"
            f"`{error.__class__.__name__}`: {error}", True)
    
    async def handle_user_input_error(self, ctx: commands.Context, e: commands.errors.UserInputError) -> None:
        if isinstance(e, commands.errors.MissingRequiredArgument):
            await ctx.send(f":x: **Missing required argument;** `{e.param.name}`")
        elif isinstance(e, commands.errors.TooManyArguments):
            await ctx.send(f":x: **Too many arguments;** `{e}`")
        elif isinstance(e, commands.errors.BadArgument):
            await ctx.send(f":x: **Bad argument;** `{e}`")
        elif isinstance(e, commands.errors.BadUnionArgument):
            await ctx.send(f":x: **Bad argument;** `{e}`\n```py\n{e.errors[-1]}\n```")
        elif isinstance(e, commands.errors.ArgumentParsingError):
            await ctx.send(f":x: **Argument parsing error;** `{e}`")
        else:
            embed = discord.Embed(
                title = "Input error",
                description = "Something about your input seems off. Check the arguments and try again.",
                colour = discord.Colour.dark_red(),
                timestamp = ctx.message.created_at
            )
            await ctx.send(embed=embed)

    async def handle_check_failure(self, ctx: commands.Context, e: commands.errors.CheckFailure) -> None:
        bot_missing_errors = (
            commands.errors.BotMissingPermissions,
            commands.errors.BotMissingRole,
            commands.errors.BotMissingAnyRole
        )

        if isinstance(e, bot_missing_errors):
            await ctx.send(":x: **It looks like I don't have permission to do that!**")
        else:
            await ctx.send(f":x: **{e}**")

    @commands.command(name='error', hidden=True)
    async def _error(self, ctx: commands.Context) -> None:
        await ctx.send(":x: **Error, Command Error!**")

def setup(bot: Bot) -> None:
    bot.add_cog(ErrorHandler(bot))