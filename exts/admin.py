# Admin stuff for the bot
# Made by Tpmonkey

from discord.ext.commands import is_owner, command, Cog, Context
from discord import Embed, Color

from utils.extensions import EXTENSIONS
import config
from bot import Bot

import logging

# These library is for admin eval command
import traceback
import datetime
import inspect
import importlib
import discord
import os

log = logging.getLogger(__name__)

class AdminCommands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.eval_jobs = {}
    
    
    def delete_eval_job(self, id: int) -> None:
        # Delete existing eval job.
        # Need except if the command has been run twice at the same time
        try:
            del self.eval_jobs[id]
        except Exception as e:
            log.trace(f"Couldn't delete eval job; {e}")
            pass
    
    @command(name="findembed")
    @is_owner()
    async def find_embed(self, ctx: Context, message_id: int, channel_id: int) -> None:
        message = await self.bot.find_message(message_id, channel_id)

        embed = message.embeds[0]
        await ctx.send(embed.to_dict())

    @command(name="say")
    @is_owner()
    async def say(self, ctx: Context, *, text: str) -> None:
        # Make the bot say something, FOR FUN (Admn only :P)
        delete = True
        text = "".join(text)

        if "--nodelete" in text or "--nod" in text:
            text = text.replace("--nodelete", "")  
            text = text.replace("--nod", "")
            delete = False        
        
        if delete:
            await ctx.message.delete()
        log.debug(f"Say: {text},  Delete: {delete}")

        await ctx.send(text)

    @command(name='admineval', aliases = ("ae", ), help = 'Admin command for testing!')
    @is_owner()
    async def _eval(self, ctx: Context, *,  code: str) -> None:
        # Admin eval command
        code = code.strip("```")
        send = True
        
        log.debug(f"Admin Eval from {ctx.author}; code: {code}")

        # Custom options
        if "--nooutput" in code:
            code = code.replace("--nooutput", "")
            send = False
        if "--delete" in code:
            code = code.replace("--delete", "")
            await ctx.message.delete()
        
        # Run the code
        if "import" in code and "exec" not in code:
            code_ = code.replace("import ", "")
            try:
                self.mod = importlib.import_module(code_)
            except:
                result = traceback.format_exc()
            else:
                result = self.mod

        else:            
            try:
                result = await eval( str(code).replace("await ", "") ) if "await" in code else eval(code)
            except:
                result = traceback.format_exc()

        # In case of output is longer than Discord allowed, I use list of embed and send it one by one
        embeds = await self._format(ctx, code, result)
        if not send:
            return
        
        self.eval_jobs[ctx.author.id] = embeds      

        for embed in self.eval_jobs[ctx.author.id]:
            if ctx.author.id not in self.eval_jobs:
                break
            
            await ctx.send(embed=embed)

        self.delete_eval_job(ctx.author.id)
    
    @command(name="adminevalstop", aliases = ("aestop", ), description = "Stop existing eval jobs")
    @is_owner()
    async def stop_eval(self, ctx: Context) -> None:
        # Stop existing Eval command
        # Sometimes the output is so long, and Bot will be spamming it

        # Check for existing jobs
        if ctx.author.id not in self.eval_jobs:
            await ctx.send(":x: You don't have any eval jobs at the moment!")
            return
        
        log.debug(f"Stop Admin Eval by {ctx.author}")

        # Delete it
        self.delete_eval_job(ctx.author.id)

        await ctx.send("Canceled all eval jobs!")

    async def _format(self, ctx: Context, code: str, result: str) -> list:
        # Format input and output of Admin Eval Command
        # To list of embed

        result_str = str(result)
        if "```" in result_str:
            result_str.replace("```", "'``")
            result = result_str
        
        results = []

        if len(result_str) > 1000:
            text = ''
            
            for i in result_str:

                text += i
                if len(text) > 1000:
                    results.append(text)
                    text = i
            results.append(text)
        
        embeds = []
        
        embed = await self._base_embed(ctx, code)

        if results != []:
            for i in range(len(results)):
                if i != 0:
                    embed = await self._base_embed(ctx, code)
                name = f"{i}"
                value = f"```python\n\n{results[i]}\n\n\n```"
                embed.add_field(name=name, value=value)
                embeds.append(embed)                
        else:
            embed.add_field(name = f"Output {type(result)}", value=f"```python\n\n{result}\n\n\n```")
            embeds.append(embed)
        
        return embeds
    
    async def _base_embed(self, ctx: Context, code: str) -> Embed:
        # Get base embed of Admin Eval command
        embed = Embed(
            title = "Evaluate Command",
            description = f"Run by {ctx.author.mention}" ,
            colour = Color.magenta(),
            timestamp = ctx.message.created_at
        )
        embed.add_field(name="Input:", value=f"```python\n\n{code}\n\n\n```", inline=False)
        return embed


    @command(name = "reload")
    @is_owner()
    async def reload(self, ctx: Context, *, file: str) -> None:
        # Reload bot Extensions

        m = await ctx.send("Reloading...")

        reload = "Succesful!"

        # Reload all extensions.
        if file.lower() == "all":
            embed = Embed(
                title = "Reload All Extensions",
                color = Color.magenta()
            )

            extensions = set(EXTENSIONS)

            for i in extensions: # Try to reload each extension one by one, and check the result.
                v = "Succesful!"
                try:
                    self.bot.reload_extension(i)
                except Exception as e:
                    v = e

                embed.add_field(name = i, value = v)
            await m.edit(embed=embed)
            return
        
        # Only one extension
        elif "exts." not in file:
            file = f"exts.{file}"

        try:
            self.bot.reload_extension(file)
        except Exception as e:
            reload = e
        await m.edit(content=reload)
    
    @command(name="shutdown")
    @is_owner()
    async def _shutdown(self, ctx: Context):
        await ctx.send("Waiting for confirmation... \nPlease type `confirm` to confirm in `10` seconds.")

        def check(m):
            return m.content.lower() == "confirm" and m.channel == ctx.message.channel and m.author.id == ctx.author.id
        
        try:
            await self.bot.wait_for('message', check=check, timeout=10)
        except:
            await ctx.send("Canceled")
            return

        await self.bot.log(__name__, "Shutting down bot... by {}".format(ctx.author.mention))

        await ctx.send("Shutting down...")
        log.info("Shutting down bot by {}".format(ctx.author))

        await self.bot.logout()


def setup(bot: Bot) -> None:
    bot.add_cog(AdminCommands(bot))