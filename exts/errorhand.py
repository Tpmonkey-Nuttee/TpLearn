# Error handler
# Made by Tpmonkey

from discord.ext.commands import Cog, Context, errors
from discord import Embed, Colour

from bot import Bot

import logging

log = logging.getLogger(__name__)


class ErrorHandler(Cog):
    def __init__(self, bot: Bot):
        self.bot =  bot

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: errors.CommandError) -> None:
        # Error handler
        command = ctx.message.content[1:]

        # Already Handled
        if hasattr(error, "handled"):
            log.trace(f"Command: {command}; Already handled locally.")
            return               

        if isinstance(error, errors.CommandNotFound):
            return
        elif isinstance(error, errors.UserInputError):
            await self.handle_user_input_error(ctx, error)
            return
        elif isinstance(error, errors.CheckFailure):
            await self.handle_check_failure(ctx, error)
            return
        elif isinstance(error, errors.CommandOnCooldown):
            await ctx.send(f":x: **{error}**")
            return
        else:
            await ctx.send(":x: **Something went wrong while processing your request!**")        

        log.debug(            
            f"Command {command} invoked by {ctx.message.author} with error "
            f"{error.__class__.__name__}: {error}"
        )
        await self.bot.log(
            __name__,
            f":negative_squared_cross_mark: Command `{command}` invoked by `{ctx.message.author}` with error \n"
            f"`{error.__class__.__name__}`: {error}",
            True
        )
    
    async def handle_user_input_error(self, ctx: Context, e: errors.UserInputError) -> None:
        if isinstance(e, errors.MissingRequiredArgument):
            await ctx.send(f":x: **Missing required argument;** `{e.param.name}`")
        elif isinstance(e, errors.TooManyArguments):
            await ctx.send(f":x: **Too many arguments;** `{e}`")
        elif isinstance(e, errors.BadArgument):
            await ctx.send(f":x: **Bad argument;** `{e}`")
        elif isinstance(e, errors.BadUnionArgument):
            await ctx.send(f":x: **Bad argument;** `{e}`\n```py\n{e.errors[-1]}\n```")
        elif isinstance(e, errors.ArgumentParsingError):
            await ctx.send(f":x: **Argument parsing error;** `{e}`")
        else:
            embed = Embed(
                title = "Input error",
                description = "Something about your input seems off. Check the arguments and try again.",
                colour = Colour.dark_red(),
                timestamp = ctx.message.created_at
            )
            await ctx.send(embed=embed)

    async def handle_check_failure(self, ctx: Context, e: errors.CheckFailure) -> None:
        bot_missing_errors = (
            errors.BotMissingPermissions,
            errors.BotMissingRole,
            errors.BotMissingAnyRole
        )

        if isinstance(e, bot_missing_errors):
            await ctx.send(":x: **It looks like I don't have permission to do that!**")
        else:
            await ctx.send(f":x: **{e}**")

def setup(bot: Bot) -> None:
    bot.add_cog(ErrorHandler(bot))