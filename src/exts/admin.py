"""
An Admin Commands Extension.
Made by Tpmonkey
"""

from discord import Embed, Color, TextChannel
from discord.ext.commands import is_owner, command, Cog, Context

from bot import Bot
from utils.extensions import EXTENSIONS

import logging

# These library is for admin eval command
import os
import sys
import math
import json
import asyncio
import inspect
import discord
import datetime
import traceback
import importlib

log = logging.getLogger(__name__)

class AdminCommands(Cog):
    """Bot admin commands"""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.eval_jobs = {}
        self.clearing = False
    
    def delete_eval_job(self, id_: int) -> None:
        """Delete existing eval job."""
        # Need except if the command has been run twice at the same time
        try:
            del self.eval_jobs[id_]
        except Exception as e:
            log.trace(f"Couldn't delete eval job; {e}")
    
    @command(name = "update")
    @is_owner()
    async def _update(self, ctx: Context, url: str = None) -> None:
        await self.bot.update(ctx, url)
    
    @command(name = "restart")
    @is_owner()
    async def _restart(self, ctx: Context) -> None:
        await ctx.send("Restarting...")
        self.bot.restart()

        
    @command(aliases = ("sc", ))
    @is_owner()
    async def stop_clearing(self, ctx: Context) -> None:
        if not self.clearing:
            return await ctx.send("No clearing to stop :/")
            
        self.clearing = False
        await ctx.send("Should be stop now.")

    
    @command(aliases = ("cm", ))
    @is_owner()
    async def clear_messages(self, ctx: Context, channel: TextChannel, limit: int, *kwargs: str) -> None:
        """Clear Messages that contain given keywords."""
        if self.clearing:
            return await ctx.send("There is a clearing in progres, please wait.\nto stop type: `!sc`")            

        count = 0
        total = 0
        self.clearing = True

        await ctx.send("Clearing - may take a long time.")

        async for message in channel.history(limit=limit):
            if not self.clearing:
                break
            
            total += 1
            # Checking for any matching kwargs in normal message content.
            content = message.content
            
            # Checking for any matching kwargs in 'embed' content.
            # Will be searching for title, description and author.
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                embed_dict = embed.to_dict()

                content += str(embed.title) + str(embed.description)

                if 'author' in embed_dict:
                    content += str(embed_dict['author']['name'])                

            if any(word in content.lower() for word in kwargs):
                try:
                    await message.delete()
                except Exception as e:
                    await ctx.send(f"Couldn't delete `{content}`\n|\n{e}")
                count += 1
                print("Deleted:", content)
                
                await asyncio.sleep(1)
            
            
        self.clearing = False
        await ctx.send(f"Found {count} messages, from total of {total} messages.")
    
    @command()
    @is_owner()
    async def count(self, ctx: Context, channel: TextChannel, limit: int, *kwargs: str) -> None:
        """Count Messages that contain given keywords."""

        count = 0

        async for message in channel.history(limit=limit):
            
            # Checking for any matching kwargs in normal message content.
            content = message.content
            
            # Checking for any matching kwargs in 'embed' content.
            # Will be searching for title, description and author.
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                embed_dict = embed.to_dict()

                content += str(embed.title) + str(embed.description)

                if 'author' in embed_dict:
                    content += str(embed_dict['author']['name'])                

            if any(word in content.lower() for word in kwargs):
                count += 1
            
        await ctx.send(f"Count: {count}")

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
            except ModuleNotFoundError:
                self.result = traceback.format_exc()
            else:
                self.result = self.mod

        else:            
            try:
                self.result = await eval( str(code).replace("await ", "") ) if "await" in code else eval(code)
            except Exception: # because it's remote execution, we do not know what error can occur.
                self.result = traceback.format_exc()

        # In case of output is longer than Discord allowed, I use list of embed and send it one by one
        embeds = await self._format(ctx, code, self.result)
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
            for i, item in enumerate(results):
                if i != 0:
                    embed = await self._base_embed(ctx, code)

                name = f"{i}"
                value = f"```python\n\n{item}\n\n\n```"
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
            return await m.edit(content=reload, embed=embed)            
        
        # Only one extension
        if "exts." not in file:
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
        except asyncio.TimeoutError:
            return await ctx.send("Canceled")            

        await self.bot.log(__name__, "Shutting down bot... by {}".format(ctx.author.mention))

        await ctx.send("Shutting down...")
        log.info("Shutting down bot by {}".format(ctx.author))   

        self.bot.unload_cogs()     
        await self.bot.close()

    @command(hidden=True)
    async def me(self, ctx: Context) -> None:
        await ctx.send("You?")

def setup(bot: Bot) -> None:
    bot.add_cog(AdminCommands(bot))