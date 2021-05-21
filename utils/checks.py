"""
Command Check, Mainly used for add command.
May add more.
Made by Tpmonkey
"""

from discord.ext import commands

class TooManyAssignments(commands.CheckFailure):
    """Exception raise when Assignments limit has been reached"""
    pass


def assignment_limit():
    """Check if assignment limit has been reached."""
    async def predicate(ctx: commands.Context):
        a = ctx.bot.planner.get_all(ctx.guild.id)
        if len(a) >= ctx.bot.config.assignment_limit:
            raise TooManyAssignments("Assignments limit has been reached. (%i)" % ctx.bot.config.assignment_limit)
        return True        
    
    return commands.check(predicate)