"""
Bot Help Command
Idea from Python Discord Bot team on Github.
Credit: https://github.com/python-discord/bot
Re-created by Tpmonkey
"""

from contextlib import suppress
from typing import List, Union
import itertools

from discord.ext.commands import Cog, HelpCommand, Command, command, Context
from discord import Embed, Colour

from bot import Bot
from pagination import LinePaginator

COMMANDS_PER_PAGE = 8

class CustomHelpCommand(HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={"help": "Shows help for bot commands"})
    
    @staticmethod
    def _category_key(command: Command) -> str:
        """
        Returns a cog name of a given command for use as a key for `sorted` and `groupby`.

        A zero width space is used as a prefix for results with no cogs to force them last in ordering.
        """
        if command.cog:
            with suppress(AttributeError):
                if command.cog.category:
                    return f"**{command.cog.category}**"
            return f"**{command.cog_name}**"
        return "**\u200bNo Category:**"
     
    def get_commands_brief_details(self, commands_: List[Command], return_as_list: bool = False) -> Union[List[str], str]:
        """
        Formats the prefix, command name and signature, and short doc for an iterable of commands.

        return_as_list is helpful for passing these command details into the paginator as a list of command details.
        """
        details = []
        for _command in commands_:
            signature = f" {_command.signature}" if _command.signature else ""
            details.append(
                f"\n**`{self.prefix}{_command.qualified_name}{signature}`**\n*{_command.short_doc or 'No details provided'}*"
            )
        if return_as_list:
            return details
        return "".join(details)

    async def command_formatting(self, command: Command) -> Embed:
        # Return Embed of command
        embed = Embed(
            title = ":grey_question: Command Help",
            colour = Colour.teal()
        )

        parent = command.full_parent_name

        name = str(command) if not parent else f"{parent} {command.name}"
        command_details = f"**```{self.context.prefix}{name} {command.signature}```**\n"

        # show command aliases
        aliases = [f"`{alias}`" if not parent else f"`{parent} {alias}`" for alias in command.aliases]
        aliases += [f"`{alias}`" for alias in getattr(command, "root_aliases", ())]
        aliases = ", ".join(sorted(aliases))
        if aliases:
            command_details += f"**Can also use:** {aliases}\n\n"

        # check if the user is allowed to run this command
        if not await command.can_run(self.context):
            command_details += "***You cannot run this command.***\n\n"

        command_details += f"*{command.help or 'No details provided.'}*\n"
        embed.description = command_details

        return embed

    async def send_command_help(self, command: Union[Command, str]) -> None:
        # Send help for a single command

        embed = await self.command_formatting(command)
        await self.context.send(embed=embed)

    async def send_bot_help(self, mapping: dict) -> None:
        """Sends help for all bot commands and cogs."""

        bot = self.context.bot

        embed = Embed(
            title = ":grey_question: Command Help",
            colour = Colour.teal()
        )

        filter_commands = await self.filter_commands(bot.commands, sort=True, key=self._category_key)

        cog_or_category_pages = []

        for cog_or_category, _commands in itertools.groupby(filter_commands, key=self._category_key):
            sorted_commands = sorted(_commands, key=lambda c: c.name)

            if len(sorted_commands) == 0:
                continue

            command_detail_lines = self.get_commands_brief_details(sorted_commands, return_as_list=True)

            # Split cogs or categories which have too many commands to fit in one page.
            # The length of commands is included for later use when aggregating into pages for the paginator.
            for index in range(0, len(sorted_commands), COMMANDS_PER_PAGE):
                truncated_lines = command_detail_lines[index:index + COMMANDS_PER_PAGE]
                joined_lines = "".join(truncated_lines)
                cog_or_category_pages.append((f"**{cog_or_category}**{joined_lines}", len(truncated_lines)))

        pages = [
            f"To find tutorial, Use **{self.context.prefix}ttr**\n\n"
            f"Found a bugs? Try checking it using **{self.context.prefix}bugs**\n"
            "It's not there? Report it by Dm-ing the bot!\n"
            "P.S. This bot is made by \"one\" person... So expect some bugs!"
        ]
        counter = 0
        page = ""
        for page_details, length in cog_or_category_pages:
            counter += length
            if counter > COMMANDS_PER_PAGE:
                # force a new page on paginator even if it falls short of the max pages
                # since we still want to group categories/cogs.
                counter = length
                pages.append(page)
                page = f"{page_details}\n\n"
            else:
                page += f"{page_details}\n\n"

        if page:
            # add any remaining command help that didn't get added in the last iteration above.
            pages.append(page)

        await LinePaginator.paginate(pages, self.context, embed=embed, max_lines=1, max_size=2000)

    async def send_cog_help(self, cog: Cog) -> None:
        """Send help for a cog."""
        # sort commands by name, and remove any the user can't run or are hidden.
        commands_ = await self.filter_commands(cog.get_commands(), sort=True)

        embed = Embed(title = ":grey_question: Command Help",)
        # embed.set_author(name="Command Help", icon_url=constants.Icons.questionmark)
        embed.description = f"**{cog.qualified_name}**\n*{cog.description}*"

        command_details = self.get_commands_brief_details(commands_)
        if command_details:
            embed.description += f"\n\n**Commands:**\n{command_details}"

        await self.context.send(embed=embed)
        

class Help(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self) -> None:
        # Reset the help command when the cog is unloaded.
        self.bot.help_command = self.old_help_command
    
    @command(hidden=True)
    async def helpme(self, ctx: Context) -> None:
        await ctx.send("How?")
    
    @command()
    async def ttr(self, ctx: Context) -> None:
        bot = ctx.bot
        embed = Embed(
            description = f"To view all the commands, Type `{ctx.prefix}help`",
            colour = Colour.teal()
        )
        embed.set_author(name = "Tutorial", icon_url = bot.user.avatar_url)

        embed.add_field(
            name = "What is this bot?", 
            value = "This bot has 3 systems. Assignment, KUS monitor, Music. Look further down to find how to use each one of three systems!",
            inline = False
        )

        embed.add_field(
            name = "1) How to use assignment system?",
            value = f"To start using, Please type down `{ctx.prefix}setup` to setup the bot.\n"
                f"After that, you can use `{ctx.prefix}add` to open assignment menu and add an assignment!\n"
                f"You can also use `{ctx.prefix}remove` or `{ctx.prefix}edit` to remove/edit it!" ,
            inline = False
        )

        embed.add_field(
            name = "2) How to use KUS monitor system?",
            value = f"To start using, Please go to TextChannel that you want the bot to send the news,\n"
                f"then type down `{ctx.prefix}set-news` to setup the bot, The bot will start sending news after it found actual **new news** Got it? :P\n"
                f"To remove use `{ctx.prefix}remove-news` and bot will stop sending it!" ,
            inline = False
        )

        embed.add_field(
            name = "3) How to use music system?",
            value = f"After the Discord Music bots shutdown, I can now be the replacement for them!\n"
                f"All the commands can be found in the commands session but They're all the same as Groovy, Rythm, etc. (Except `remove` command is changed to `removes`)\n"
                f"Please Note that, This bot is made by one person. if you found any bugs, Please use `{ctx.prefix}leave` and then resummon me again!\n" 
                "Also, You can Direct Message bot directly to inform about the bug and I will patch it ASAP!",
            inline = False
        )

        embed.add_field(
            name = "EXTRA) How to use assignment menu?",
            value = f"You can open it using `{ctx.prefix}add` `{ctx.prefix}remove` or `{ctx.prefix}edit`"
                f"After it's opened, You can **type down like you're talking in a normal conversation**! The bot will delete it and input it into the system!\n"
                f"To insert date, You have 2 ways to do. First way is to type the full date in this format `Day/Month/Year` (*Example: 1/1/2021 or 22/2/2005*)\n" 
                f"Second way is to use `++days` (*Example: ++1 meaning tomorrow*)\n"
                f"To insert image, You can send the file directly or You can also send a hyper link to the image source!",
            inline = False
        )

        embed.set_footer(text = "Created by Tpmonkey#2682 as a Senior Project.")
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Help(bot))