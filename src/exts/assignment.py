"""
An Assignment Manger, Main Extension for input.
Made by Tpmonkey
"""

import discord 
from discord.ext import commands

from bot import Bot
from utils import checks
from utils.time import today_th

import random
import asyncio 
import logging
import datetime
import traceback

# Setup some value to use later. :)
TITLES = {
    "title": ("{} Title", 1), 
    "description": ("{} Description", 2), 
    "date": ("{} Date", 3), 
    "image": ("{} Image", 4)
}
EMOJI_STRING = (":one:", ":two:", ":three:", ":four:", ":arrow_left: ")
EMOJIS = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "✅", "❎")

log = logging.getLogger(__name__)

class Assignments(commands.Cog):
    """Assignment System, Need to use `,setup` first before using it."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.tasks = {}
    
    def init_data(self, ctx: commands.Context, type_: str, **kwargs) -> None:
        """Init data when using menu."""
        log.debug(f'init dat for {ctx.author.id}')
        self.tasks[ctx.author.id] = {
            "details":{
                "type": type_, "state": 1, "key": kwargs.get("key"),
                "image": kwargs.get('image-url', "Not Attached"),
                "headers":{
                    "title": kwargs.get('title', "Untitled"),
                    "description": kwargs.get('desc', "No Description Provided"),
                    "date": kwargs.get('date', "Unknown"),
                }},
            "info":{                
                "ctx": ctx, "message": None, "task": None
            }}
    
    @staticmethod
    def close_embed(reason: str, colour: discord.Colour = discord.Colour.dark_red()) -> discord.Embed:
        """Create a Closed Embed."""
        embed = discord.Embed(colour = colour)
        embed.title = "[Closed Menu]" if reason is None else reason

        return embed
    
    @staticmethod
    def get_title_from_key(key: str, state: int) -> str:
        """Create Field Title."""
        title, crrent = TITLES[key] # Get an Title and Index of title.

        # If that title is selected, Add an arrow emoji to it.
        return f"{title.format('⭕')} {EMOJI_STRING[4]*3}" if crrent == state else title.format(EMOJI_STRING[crrent-1])

    def base_embed(self, ctx: commands.Context) -> discord.Embed:
        """Create All Embed, Ready to update."""

        embed = discord.Embed(
            description = "Click the reaction to select and edit.",
            colour = discord.Colour.teal(),
            timestamp = ctx.message.created_at
        )

        embed.set_author(name = "Homework Menu", icon_url = ctx.author.avatar_url)
        embed.set_footer(text = "Send message to set info!")

        # Declare variable to use later.
        details = self.tasks[ctx.author.id]["details"]
        header = details["headers"]
        state = details["state"]
        
        # Create a header, Not including Image because It will be process later on.
        for n in header:
            name = self.get_title_from_key(n, state)
            value = self.bot.planner.get_readable_date(header[n])
            embed.add_field(name=name, value=value, inline=False)

        # Check if Image Attached or not
        if details["image"] != "Not Attached":
            # Image Attached, Attach add it into embed.
            embed.set_image(url=details["image"])
        else:
            # If not, Add field instead.
            embed.add_field(
                name=self.get_title_from_key("image", state), value = details["image"], inline=False
            )
        return embed
    
    async def listed_embed(self, ctx: commands.Context, data: dict = None) -> tuple:
        """Create a list embed with all the works."""

        # If data wasn't provided, Get it from system
        if data is None: 
            data = self.bot.planner.get_all(ctx.guild.id)

        type_ = len(data) == 0
        embed = self.bot.planner.get_embed(ctx.guild.id)
        
        return type_, embed

    async def update_embed(self, ctx: commands.Context) -> None:
        """Update Embed (Menu)"""
        if ctx.author.id not in self.tasks: 
            return

        message = self.tasks[ctx.author.id]["info"]["message"]        
        if message is None:  # If embed has been deleted or not in the data yet.
            return
     
        embed = self.base_embed(ctx)
        try: 
            await message.edit(embed=embed)
        except discord.HTTPException: # Embed has been deleted, Will close everything.
            await ctx.send(":x: **Something went wrong - canceled all actions!**")
            log.warning(f"something went wrong in homework menu for {ctx.author.id}")
            return await self.close(ctx)            
        else: 
            log.debug(f'update embed successfully for {ctx.author.id}')
    
    async def close(self, ctx: commands.Context, reason: str = None, colour: discord.Colour = discord.Colour.dark_red()) -> None:
        """Close the menu."""
        if ctx.author.id not in self.tasks: 
            return
        if self.tasks[ctx.author.id]['details']['state'] == 0: 
            return
        
        # Preventing double close and Event Bug.
        self.tasks[ctx.author.id]['details']['state'] = 0
        message = self.tasks[ctx.author.id]["info"]["message"]

        try:            
            await message.clear_reactions()
            await message.edit(embed=self.close_embed(reason, colour))     
            self.tasks[ctx.author.id]['info']['task'].cancel()
            del self.tasks[ctx.author.id]       
        except (
            # Clear reactions, edit message
            discord.HTTPException, discord.Forbidden,
            # Not sure if Task.cancel() will raise any exceptions.
            # del dict
            KeyError

        ): 
            pass
        log.debug(f"Deleted key: {ctx.author.id}")
    
    @commands.command()
    @commands.guild_only()
    @checks.assignment_limit()
    @checks.is_setup()
    @commands.cooldown(3, 45, commands.BucketType.guild)
    async def add(self, ctx: commands.Context) -> None:
        """Add an Assignment Command."""
        if ctx.author.id in self.tasks: 
            del self.tasks[ctx.author.id]

        self.init_data(ctx, 'add')
        embed = self.base_embed(ctx)

        message = await ctx.send(embed=embed)
        self.tasks[ctx.author.id]["info"]["message"] = message

        asyncio.create_task(self.bot.add_reactions(message, EMOJIS))
        self.tasks[ctx.author.id]['info']['task'] = asyncio.create_task(self.adding(ctx))         
    
    @commands.command()
    @commands.guild_only()
    @checks.is_setup()
    @commands.cooldown(3, 45, commands.BucketType.guild)
    async def edit(self, ctx: commands.Context, key: str = None) -> None:
        """Edit an Assignment Command."""
        if ctx.author.id in self.tasks: 
            del self.tasks[ctx.author.id]
        
        if key is None or not self.bot.planner.check_valid_key(ctx.guild.id, key):
            type_, embed = await self.listed_embed(ctx) 

            content = None if type_ else "Please the assignment key to edit!"
            return await ctx.send(content, embed=embed)
            
        
        d = self.bot.planner.get(ctx.guild.id, key)
        if d['already-passed']:
            return await ctx.send(":x: **You shouldn't edit already passed assignment.**")
            
        
        self.init_data(ctx, 'edit', **d)

        embed = self.base_embed(ctx)
        message = await ctx.send(embed=embed)        
        self.tasks[ctx.author.id]["info"]["message"] = message

        asyncio.create_task(self.bot.add_reactions(message, EMOJIS))
        self.tasks[ctx.author.id]['info']['task'] = asyncio.create_task(self.adding(ctx))     
    
    @commands.command(aliases = ("delete", "del", ))
    @commands.guild_only()
    @checks.is_setup()
    @commands.cooldown(3, 15, commands.BucketType.guild)
    async def remove(self, ctx: commands.Context, key: str = None) -> None:
        """Remove an Assignments"""
        data = self.bot.planner.get_all(ctx.guild.id)
    
        if not self.bot.planner.check_valid_key(ctx.guild.id, key) or len(data) == 0:
            type_, embed = await self.listed_embed(ctx, data)
            content = None if type_ else "Please the assignment key to delete!"
        else:
            d = await self.bot.planner.remove(ctx.guild.id, key)

            embed = discord.Embed()
            embed.colour = discord.Colour.blue()
            embed.timestamp = ctx.message.created_at
            embed.description = f"**Removed** `{d.get('key')}`"

            content = ""
        
        await ctx.send(content, embed=embed)
    
    @commands.command(aliases = ("aw", "allassignments", )) # Why?
    @commands.guild_only()
    @checks.is_setup()
    @commands.cooldown(2, 20, commands.BucketType.guild)
    async def allworks(self, ctx: commands.Context) -> None:
        """Show all Assignments"""

        m = await ctx.send("Creating Embed...")

        d = self.bot.planner.get_all(ctx.guild.id)
        _, embed = await self.listed_embed(ctx, d)

        await m.edit(content=None, embed=embed)

    @commands.command(aliases = ('inf', 'detail', 'check', ))
    @commands.guild_only()
    @checks.is_setup()
    @commands.cooldown(5, 25, commands.BucketType.guild)
    async def info(self, ctx: commands.Context, key: str = None) -> None:
        """Info about the Assignments"""
        data = self.bot.planner.get_all(ctx.guild.id)

        if len(data) == 0:
            return await ctx.send("No assignment yet!")                    

        content = None
        if not self.bot.planner.check_valid_key(ctx.guild.id, key):
            content = "Please the assignment key to check assignment info!"
            _, embed = await self.listed_embed(ctx, data)
        else:
            info = self.bot.planner.get(ctx.guild.id, key)
            embed = self.bot.get_embed(**info)
        
        await ctx.send(content, embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self.process_reaction_event(payload)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self.process_reaction_event(payload)
    
    async def process_reaction_event(self, payload: discord.RawReactionActionEvent) -> None:
        """
        Process Reaction event.

        Checks:
            * Emoji is in the list.
            * User has a menu opened.
            * State of menu needs to be valid.

        """
        emoji = str(payload.emoji)
        
        if emoji not in EMOJIS or \
        payload.user_id not in self.tasks or \
        self.tasks[payload.user_id]['details']['state'] == 0:
            return
        
        ctx = self.tasks[payload.user_id]["info"]["ctx"]
        old_state = self.tasks[payload.user_id]["details"]["state"]
        log.debug(f'processing {emoji} for {ctx.author.id}')

        if emoji == "❎": # Close menu            
            return await self.close(ctx)    
        if emoji == "✅":
            return await self.finish_request(ctx)

        if emoji == "1️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 1
        elif emoji == "2️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 2
        elif emoji == "3️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 3
        elif emoji == "4️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 4
        
        if old_state != self.tasks[payload.user_id]["details"]["state"]:
            # update if the state changed.
            await self.update_embed(ctx)

    async def adding(self, ctx: commands.Context) -> None:
        """
        A method that will get an input from target message, and delete it.
        """
        while ctx.author.id in self.tasks:
            try:
                message = await self.bot.wait_for_message(ctx, timeout = 300)
            except asyncio.TimeoutError:
                return await self.close(ctx)       
            
            # Checks:
            # -* Message content is not bot command.
            # -* Menu is open & State is valid.

            if ctx.author.id not in self.tasks or \
            self.tasks[ctx.author.id]['details']['state'] == 0:
                return

            content = message.content
            log.debug(f"Recieve message: {content}")
                        
            if content is not None and content.startswith(self.bot.command_prefix):
                log.debug("content startswith command prefix.")
                return await self.close(ctx, reason = "Use another bot's command.")     
            
            # Delete message
            await message.delete()

            # Shortcuts
            if content.startswith("-"):
                content = content.lstrip("-")
                args = content.split()

                if len(args) < 1:
                    await self.handle_request(ctx, message)

                # goto command
                elif args[0].lower() == "goto" or args[0].lower() == "gt":
                    try:
                        _state = int(args[1])
                    except IndexError:
                        await ctx.send(":x: **Invalid args; state is needed.**", delete_after=10)
                    except ValueError:
                        await ctx.send(":x: **Invalid args; state needs to be number**", delete_after=10)
                    else:
                        if 1 <= _state <= 4:
                            self.tasks[ctx.author.id]["details"]["state"] = _state
                        else:
                            await ctx.send(":x: **Invalid args: state need to be between 1 - 4.**", delete_after=10)
                elif args[0].lower() == "cancel" or args[0].lower() == "exit":
                    await self.close(ctx)
                elif args[0].lower() == "finish" or args[0].lower() == "done":
                    await self.finish_request(ctx)
                else:
                    await self.handle_request(ctx, message)
            else:
                await self.handle_request(ctx, message)      
            
            await self.update_embed(ctx)
    
    async def handle_request(self, ctx: commands.Context, message: discord.Message) -> None:
        content = message.content
        state = self.tasks[ctx.author.id]["details"]["state"]

        # If the content is None, It's likely to be a picture file.
        if not content.strip():
            log.debug("empty message, likely to be picture")
            state = 4

        if state == 1:
            self.tasks[ctx.author.id]["details"]["headers"]["title"] = content
        elif state == 2:
            self.tasks[ctx.author.id]["details"]["headers"]["description"] = content
        elif state == 3:
            self.tasks[ctx.author.id]["details"]["headers"]["date"] = self.format(content)
        else:
            image_url = self.tasks[ctx.author.id]["details"]["image"] 
            if len(message.attachments) < 1:
                if ("http://" in content or "https://" in content) and "." in content:
                    image_url = content
                    log.debug(f'{ctx.author.id} added image using url: {image_url}')
            else:
                log.debug(f'{ctx.author.id} added image using file')
                image = message.attachments[0]
                image_url = await self.bot.get_image_url(image)
            
            self.tasks[ctx.author.id]["details"]["image"] = image_url
        
        # Update state.
        self.tasks[ctx.author.id]["details"]["state"] = state + 1 if state < 4 else 1   
    
    async def finish_request(self, ctx: commands.Context) -> None:
        type_ = self.tasks[ctx.author.id]['details']['type']

        if self.bot.planner.check_passed_date(self.tasks[ctx.author.id]["details"]["headers"]["date"]):
            log.debug(f'{ctx.author.id} tried to add/edit passed assignment.')
            return await self.close(ctx, "Cannot add/edit already passed assignment.")
            
        
        title = self.tasks[ctx.author.id]["details"]["headers"]["title"]
        description = self.tasks[ctx.author.id]["details"]["headers"]["description"]
        date = self.tasks[ctx.author.id]["details"]["headers"]["date"]
        image_url = self.tasks[ctx.author.id]["details"]["image"]

        if all( 
            (title == "Untitled", description == "No Description Provided", 
            date == "Unknown", image_url == "Not Attached") 
        ): 
            log.debug(f'{ctx.author.id} tried to add/edit to invalid assignement.')
            return await self.close(ctx, "Invalid Assignment")
            
        
        try:
            ret = await self.bot.planner.add(
                ctx.guild.id,
                title = title,
                description = description,
                date = date,
                image_url = image_url,
                key = self.tasks[ctx.author.id]['details']['key']
            )

        except Exception:                
            text = f"Unable to {type_} Assignment, Problem has been reported."
            log.warning(f'something went wrong while {ctx.author.id} add/edit in homework menu')
            log.warning(traceback.format_exc())
            await self.bot.log(__name__, f"An Exception were found while finishing adding assignment\n```py\n{traceback.format_exc()}\n```", True)
            colour = discord.Colour.default()

        else:
            text = f"Successfully Added Assignment with key `{ ret }`" if type_ == 'add' \
            else "Successfully Edited Assignment."
            colour = discord.Colour.teal()
            log.debug(f'{ctx.author.id} add/edit new assignment and passed in successfully.')
        
        return await self.close(ctx, text, colour)

    @commands.command(hidden=True)
    async def school(self, ctx: commands.Context) -> None:
        if random.randint(1, 1000) == 1:
            return await ctx.send("Sucks")
        await ctx.send("Good place.")

    @staticmethod
    def format(text: str) -> str:
        if text.startswith("++") and len(text.split()) == 1:
            _text = text.lstrip("++").lstrip("-")

            try:
                _days = int(_text)
            except ValueError:
                return text
            
            future = today_th(True) + datetime.timedelta(days = _days)
            return "{0.day}/{0.month}/{0.year}".format(future)
        return text


def setup(bot: Bot) -> None:
    bot.add_cog(Assignments(bot))