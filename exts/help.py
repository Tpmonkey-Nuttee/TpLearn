# Custom Help command for the Bot
# Made by Tpmonkey
# Credit: Python Discord

from contextlib import suppress
from typing import List, Union
import itertools

from discord.ext.commands import Cog, HelpCommand, Command
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
        else:
            return "**\u200bNo Category:**"
    
    @staticmethod    
    def get_commands_brief_details(commands_: List[Command], return_as_list: bool = False) -> Union[List[str], str]:
        """
        Formats the prefix, command name and signature, and short doc for an iterable of commands.

        return_as_list is helpful for passing these command details into the paginator as a list of command details.
        """
        details = []
        for command in commands_:
            signature = f" {command.signature}" if command.signature else ""
            details.append(
                f"\n**`{PREFIX}{command.qualified_name}{signature}`**\n*{command.short_doc or 'No details provided'}*"
            )
        if return_as_list:
            return details
        else:
            return "".join(details)

    async def command_formatting(self, command: Command) -> Embed:
        # Return Embed of command
        embed = Embed(
            title = ":grey_question: Command Help",
            colour = Colour.teal()
        )

        parent = command.full_parent_name

        name = str(command) if not parent else f"{parent} {command.name}"
        command_details = f"**```{PREFIX}{name} {command.signature}```**\n"

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

    async def send_command_help(self, command: Command) -> None:
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

        pages = []
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
    

class Help(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

        global PREFIX
        PREFIX = self.bot.command_prefix
    
    def cog_unload(self) -> None:
        # Reset the help command when the cog is unloaded.
        self.bot.help_command = self.old_help_command


def setup(bot: Bot) -> None:
    bot.add_cog(Help(bot))