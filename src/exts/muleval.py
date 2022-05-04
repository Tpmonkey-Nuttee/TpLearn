"""
Eval Command
Idea from Python Discord Bot team on Github.
Credit: https://github.com/python-discord/bot
Re-created by Tpmonkey
"""

from discord.ext.commands import Cog, command, Context, guild_only, is_owner
from discord import Embed, Colour

from utils.post_eval import post_eval

import textwrap
import logging
import re

ESCAPE_REGEX = re.compile("[`\u202E\u200B]{3,}")

FORMATTED_CODE_REGEX = re.compile(
    r"(?P<delim>(?P<block>```)|``?)"        # code delimiter: 1-3 backticks; (?P=block) only matches if it's a block
    r"(?(block)(?:(?P<lang>[a-z]+)\n)?)"    # if we're in a block, match optional language (only letters plus newline)
    r"(?:[ \t]*\n)*"                        # any blank (empty or tabs/spaces only) lines before the code
    r"(?P<code>.*?)"                        # extract all code inside the markup
    r"\s*"                                  # any more whitespace before the end of the code markup
    r"(?P=delim)",                          # match the exact same delimiter from the start again
    re.DOTALL | re.IGNORECASE               # "." also matches newlines, case insensitive
)
RAW_CODE_REGEX = re.compile(
    r"^(?:[ \t]*\n)*"                       # any blank (empty or tabs/spaces only) lines before the code
    r"(?P<code>.*?)"                        # extract all the rest as code
    r"\s*$",                                # any trailing whitespace until the end of the string
    re.DOTALL                               # "." also matches newlines
)

BLACK_LIST = (
    "open", "os", "token", "exit", "shutdown", "bot", "main"
)

log = logging.getLogger(__name__)

class Snekbox(Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def prepare_input(code: str, ignore_black_list: bool) -> str:
        if match := list(FORMATTED_CODE_REGEX.finditer(code)):
            blocks = [block for block in match if block.group("block")]

            if len(blocks) > 1:
                code = '\n'.join(block.group("code") for block in blocks)
                info = "several code blocks"
            else:
                match = match[0] if len(blocks) == 0 else blocks[0]
                code, block, lang, delim = match.group("code", "block", "lang", "delim")
                if block:
                    info = (f"'{lang}' highlighted" if lang else "plain") + " code block"
                else:
                    info = f"{delim}-enclosed inline code"
        else:
            code = RAW_CODE_REGEX.fullmatch(code).group("code")
            info = "badly formated code"
        log.info(info)

        code = textwrap.dedent(code)

        if not ignore_black_list:
            log.debug("Checking for black list word")
            for i in BLACK_LIST:
                if i in code.lower():
                    return "Black list word found!"

        return code
    
    @staticmethod
    def format_output(output: str) -> str:        
        if ESCAPE_REGEX.findall(output):
            return "Code block escape attempt detected; will not output result"        

        output = output.lstrip("\n")
        lines = output.count("\n")

        if lines > 0:
            output = [f"{i:03d} | {line}" for i, line in enumerate(output.split('\n'), 1)]
            output = output[:20]  # Limiting to only 21 lines
            output = "\n".join(output)

        if lines > 19:
            if len(output) >= 900:
                output = f"{output[:900]}\n... (truncated - too long, too many lines)"
            else:
                output = f"{output}\n... (truncated - too many lines)"

        elif len(output) >= 900:
            output = f"{output[:900]}\n... (truncated - too long)"

        output = output or "[No Output]"
        
        return output
    
    @staticmethod
    def predict_colour(rcode: str) -> Colour:
        if rcode == "0":
            return Colour.dark_green()
        if rcode == "1":
            return Colour.dark_red()
        return Colour.default()

    @command(name="eval", aliases = ("e", ))
    @guild_only()
    @is_owner()
    async def eval_command(self, ctx: Context, *, code: str = None) -> None:
        if not code:
            return await ctx.send(":x: Invalid Args, Code is needed")            

        embed = Embed(description="This command will only run the code for 10 seconds; futher than that will be terminate!")
        embed.set_author(name="Executing Code...")        
        m = await ctx.send(embed=embed)

        owner = await self.bot.is_owner(ctx.author)
        ignore = True if owner else False
        
        log.debug(f"Eval command; Ignore black list: {ignore}")
        code = self.prepare_input(code, ignore)
        if code == "Black list word found!":
            embed = Embed(
                colour=Colour.dark_red(),
                description = "Found black-listed key word in your code!\nYour Job has been canceled."
            )
            embed.set_author(name="Execution Terminated")
            return await m.edit(embed=embed)
            
        
        log.trace(f"Eval command: {ctx.author}({ctx.author.id}) with code:\n{code}")
        
        result = await post_eval(code, ctx.author.id)
        output, rcode = result
        output = self.format_output(output)

        embed = Embed(
            title = f"Exit code: {rcode}",
            colour = self.predict_colour(str(rcode))
        )
        value = f"```python\n\n{output}\n```"
        embed.add_field(name="Full Output", value=value)

        await m.edit(embed=embed)
        


def setup(bot) -> None:
    bot.add_cog(Snekbox(bot))