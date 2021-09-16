"""
Command Check, Mainly used for add command.
May add more.
Made by Tpmonkey
"""

from discord.ext import commands

class TooManyAssignments(commands.CheckFailure):
    """Exception raise when Assignments limit has been reached."""
    pass

class NotSetupYet(commands.CheckFailure):
    """Exception raise when the given guild hasn't setup the bot yet."""
    pass


def assignment_limit():
    """Check if assignment limit has been reached."""
    async def predicate(ctx: commands.Context):
        a = ctx.bot.planner.get_all(ctx.guild.id)
        if len(a) >= ctx.bot.config.assignment_limit:
            raise TooManyAssignments(
            f"Assignments limit has been reached. ({ctx.bot.config.assignment_limit})" 
        )
        return True        
    
    return commands.check(predicate)

def is_setup():
    """Check if that server is already setup the bot or not."""
    async def predicate(ctx: commands.Context):
        a = ctx.bot.manager.get(ctx.guild.id)
        if len(a) == 0:
            raise NotSetupYet(
                f"This guild isn't setup yet! Use `{ctx.bot.config.prefix}setup` to setup!" 
            )
        return True        
    
    return commands.check(predicate)