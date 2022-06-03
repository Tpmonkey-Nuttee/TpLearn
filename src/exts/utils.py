"""
Utility and Fun Commands.
Made by Tpmonkey
"""

from discord import Embed, Colour
from discord.ext.commands import Cog, Context, command, guild_only

from bot import Bot
from utils import time as timef

import random
import textwrap

class Utility(Cog):
    """
    Utility commands, just for fun of cause!
    """
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @command(hidden=True)
    @guild_only()
    async def user(self, ctx: Context) -> None:
        """Check information about yourself."""
        created = timef.time_since(ctx.author.created_at, max_units=3)
        name = str(ctx.author.name)

        if ctx.author.nick:
            name = f"{ctx.author.nick} ({name})"	            

        joined = timef.time_since(ctx.author.joined_at, max_units=3)
        roles = ", ".join(role.mention for role in ctx.author.roles[1:])

        fields = [
        (
            "User information",
            textwrap.dedent(f"""
                Created: {created}
                Profile: {ctx.author.mention}
                ID: {ctx.author.id}
            """).strip()
        ),
        (
            "Member information",
            textwrap.dedent(f"""
                Joined: {joined}
                Roles: {roles or None}
            """).strip()
        ),
        ]

        embed = Embed(
            title=name,
        )

        for field_name, field_content in fields:
            embed.add_field(name=field_name, value=field_content, inline=False)

        embed.set_thumbnail(url=ctx.author.avatar_url_as(static_format="png"))
        embed.colour = ctx.author.top_role.colour if roles else Colour.blue()

        await ctx.send(embed=embed)
    
    @command()
    async def bugs(self, ctx: Context) -> None:
        """List of known bugs."""
        embed = Embed(
            title = "Known Bugs",
            description = "This embed shows list of known bugs, Please dm the bot if you found more.",
            colour = Colour.dark_red(),
            timestamp = ctx.message.created_at
        )

        embed.add_field(
            name = "1) When using Music command, Sometimes bot doesn't play anything.",
            value = "This bug is caused by Youtube Service problem, Currently I couldn't find a way to fix it.\nBut you can use leave command and rejoin bot again to fix it.",
            inline = False
        )

        embed.add_field(
            name = "2) KUS news system sometimes sent the same news.",
            value = "This bug is caused by the website itself. How the news system work is to detect changes on the first announcement page\n"
            "and sometimes, They deleted/changed the announcement which the bot sees it as a change so it sent the news embed.\n"
            "Simply, just ignore it. The chance of it is pretty low, but I will keep an eyes on it and will implement new system is needed.",
            inline = False
        )

        embed.add_field(
            name = "3) Bot stopped playing song and quit the voice channel.",
            value = "There are lots of ways that this bug will happen but 90% of which is caused by bot restarting.\n"
            "Simply, wait a bit then try rejoining the bot again. (You can also check bot status to see if it's restarting.)",
            inline = False
        )

        await ctx.send(embed=embed)

    @command(aliases = ('fact', 'tips', 'tip', 'qoute', ))
    async def facts(self, ctx: Context) -> None:
        """Some random facts, tips, qoutes"""
        f = random.choice(self.bot.config.facts)
        if "youtube" in f:
            content = None
            embed = Embed(description = f, colour = Colour.blue())
        else:
            content = f
            embed = None
        await ctx.send(content = content, embed=embed)
    
    @command(aliases = ('ver', 'patch', ))
    async def version(self, ctx: Context) -> None:
        embed = Embed(
            title = f"Version {self.bot.config.version}",
            colour = Colour.blue(),
            timestamp = ctx.message.created_at
        )
        value = "\n".join(self.bot.config.note) if len(self.bot.config.note) != 0 else "No patch note were found."
        embed.add_field(name="Patch Notes:", value = value)
        await ctx.send(embed=embed)
    
    @command(aliases = ('inv', ) )
    async def invite(self, ctx: Context) -> None:
        embed = Embed(
            title = "Invite Link",
            description = "[Click Here](https://discord.com/oauth2/authorize?client_id=728482604747194418&scope=bot&permissions=76816)",
            colour = Colour.blue()
        )
        await ctx.send(embed=embed)

    @command(hidden=True)
    async def hello(self, ctx: Context) -> None:
        await ctx.author.move_to(None)
        await ctx.send("Hello World!")
    

def setup(bot: Bot) -> None:
    bot.add_cog(Utility(bot))