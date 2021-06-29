"""
An Assignment Manger, Main Extension for input.
Made by Tpmonkey
"""

from discord.ext.commands import Cog, Context, command, guild_only, cooldown, BucketType
from discord import Embed, Colour, RawReactionActionEvent, HTTPException

from utils import checks
from bot import Bot

from asyncio import sleep
import traceback
import logging
import random

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

class Assignments(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.tasks = {}
    
    def init_data(self, ctx: Context, type_: str, **kwargs) -> None:
        """Init data when using menu."""
        log.debug(f'init dat for {ctx.author.id}')
        self.tasks[ctx.author.id] = {
            "details":{
                "type": type_, "state": 1, "key": kwargs.get("key"),
                "image": kwargs.get('image-url', "Not Attached"),
                "headers":{
                    "title": kwargs.get('title', "Untitled"),
                    "description": kwargs.get('desc', "No Description Provied"),
                    "date": kwargs.get('date', "Unknown"),
                }},
            "info":{                
                "ctx": ctx, "message": None
            }}
    
    @staticmethod
    def close_embed(reason: str, colour: Colour = Colour.dark_red()) -> Embed:
        """Create a Closed Embed."""
        embed = Embed(colour = colour)
        embed.title = "[Closed Menu]" if reason is None else reason

        return embed
    
    @staticmethod
    def get_title_from_key(key: str, state: int) -> str:
        """Create Field Title."""
        title, crrent = TITLES[key] # Get an Title and Index of title.

        # If that title is selected, Add an arrow emoji to it.
        return f"{title.format('⭕')} {EMOJI_STRING[4]*3}" if crrent == state else title.format(EMOJI_STRING[crrent-1])

    def base_embed(self, ctx: Context) -> Embed:
        """Create All Embed, Ready to update."""

        embed = Embed(
            description = "Click the reaction to select and edit.",
            colour = Colour.teal(),
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
    
    async def listed_embed(self, ctx: Context, data: dict = None) -> tuple:
        """Create a list embed with all the works."""

        # If data wasn't provided, Get it from system
        if data is None: data = self.bot.planner.get_all(ctx.guild.id)

        type_ = len(data) == 0
        embed = self.bot.planner.get_embed(ctx.guild.id)
        
        return type_, embed

    async def update_embed(self, ctx: Context) -> None:
        """Update Embed (Menu)"""
        message = self.tasks[ctx.author.id]["info"]["message"]
         # If embed has been deleted or not in the data yet.
        if message is None: return
     
        embed = self.base_embed(ctx)
        try: await message.edit(embed=embed)
        except HTTPException: # Embed has been deleted, Will close everything.
            await ctx.send(":x: **Something went wrong - canceled all actions!**")
            log.warning(f"something went wrong in homework menu for {ctx.author.id}")
            await self.close(ctx)
            return
        else: log.debug(f'update embed successfully for {ctx.author.id}')
    
    async def close(self, ctx: Context, reason: str = None, colour: Colour = Colour.dark_red()) -> None:
        """Close the menu."""
        if ctx.author.id not in self.tasks: return
        if self.tasks[ctx.author.id]['details']['state'] == 0: return
        
        # Preventing double close and Event Bug.
        self.tasks[ctx.author.id]['details']['state'] = 0
        message = self.tasks[ctx.author.id]["info"]["message"]
        try:
            await message.clear_reactions()
            await message.edit(embed=self.close_embed(reason, colour))
        except: pass
        # Ignore all exception, Our task is already done.
        
        await sleep(2) # this is a cooldown system.
        
         # Can also use try but this is easier.
        if ctx.author.id in self.tasks: del self.tasks[ctx.author.id]
    
    @command()
    @guild_only()
    @checks.assignment_limit()
    @cooldown(2, 45, BucketType.guild)
    async def add(self, ctx: Context) -> None:
        """Add an Assignment Command."""
        if ctx.author.id in self.tasks: del self.tasks[ctx.author.id]

        self.init_data(ctx, 'add')
        embed = self.base_embed(ctx)

        message = await ctx.send(embed=embed)
        self.tasks[ctx.author.id]["info"]["message"] = message
        await self.bot.add_reactions(message, EMOJIS)
        await self.adding(ctx)
    
    @command()
    @guild_only()
    @cooldown(2, 45, BucketType.guild)
    async def edit(self, ctx: Context, key: str = None) -> None:
        """Edit an Assignment Command."""
        if ctx.author.id in self.tasks: del self.tasks[ctx.author.id]
        
        if key is None or not self.bot.planner.check_valid_key(ctx.guild.id, key):
            type_, embed = await self.listed_embed(ctx) 
            content = None if type_ else "Please the assignment key to edit!"
            await ctx.send(content, embed=embed)
            return
        
        d = self.bot.planner.get(ctx.guild.id, key)
        if d['already-passed']:
            await ctx.send(":x: **You shouldn't edit already passed assignment.**")
            return
        
        self.init_data(ctx, 'edit', **d)

        embed = self.base_embed(ctx)
        message = await ctx.send(embed=embed)
        self.tasks[ctx.author.id]["info"]["message"] = message
        await self.bot.add_reactions(message, EMOJIS)
        await self.adding(ctx)
    
    @command(aliases = ("delete", "del", ))
    @guild_only()
    @cooldown(3, 15, BucketType.guild)
    async def remove(self, ctx: Context, key: str = None) -> None:
        """Remove an Assignments"""
        data = self.bot.planner.get_all(ctx.guild.id)
    
        if not self.bot.planner.check_valid_key(ctx.guild.id, key) or len(data) == 0:
            type_, embed = await self.listed_embed(ctx, data)
            content = None if type_ else "Please the assignment key to delete!"
        else:
            d = await self.bot.planner.remove(ctx.guild.id, key)

            embed = Embed()
            embed.colour = Colour.blue()
            embed.timestamp = ctx.message.created_at
            embed.description = f"**Removed** `{d.get('key')}`"

            content = ""
        
        await ctx.send(content, embed=embed)
    
    @command(aliases = ("aw", "allassignments", )) # Why?
    @guild_only()
    @cooldown(2, 20, BucketType.guild)
    async def allworks(self, ctx: Context) -> None:
        """Show all Assignments"""

        m = await ctx.send("Creating Embed...")

        d = self.bot.planner.get_all(ctx.guild.id)
        type_, embed = await self.listed_embed(ctx, d)

        await m.edit(content=None, embed=embed)

    @command(aliases = ('inf', 'detail', 'check', ))
    @guild_only()
    @cooldown(5, 25, BucketType.guild)
    async def info(self, ctx: Context, key: str = None) -> None:
        """Info about the Assignments"""
        data = self.bot.planner.get_all(ctx.guild.id)

        if len(data) == 0:
            await ctx.send("No assignment yet!")
            return        

        content = None
        if not self.bot.planner.check_valid_key(ctx.guild.id, key):
            content = "Please the assignment key to check assignment info!"
            type_, embed = await self.listed_embed(ctx, data)
        else:
            info = self.bot.planner.get(ctx.guild.id, key)
            embed = self.bot.get_embed(**info)
        
        await ctx.send(content, embed=embed)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        await self.process_reaction_event(payload)
    
    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent) -> None:
        await self.process_reaction_event(payload)
    
    async def process_reaction_event(self, payload: RawReactionActionEvent) -> None:
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
            await self.close(ctx)
            return        
        elif emoji == "✅":
            type_ = self.tasks[ctx.author.id]['details']['type']

            if self.bot.planner.check_passed_date(self.tasks[ctx.author.id]["details"]["headers"]["date"]):
                log.debug(f'{ctx.author.id} tried to add/edit passed assignment.')
                await self.close(ctx, "Cannot add/edit already passed assignment.")
                return
            
            title = self.tasks[ctx.author.id]["details"]["headers"]["title"]
            description = self.tasks[ctx.author.id]["details"]["headers"]["description"]
            date = self.tasks[ctx.author.id]["details"]["headers"]["date"]
            image_url = self.tasks[ctx.author.id]["details"]["image"]

            if all( 
                (title == "Untitled", description == "No Description Provied", 
                date == "Unknown", image_url == "Not Attached") 
            ): 
                log.debug(f'{ctx.author.id} tried to add/edit to invalid assignement.')
                await self.close(ctx, "Invalid Assignment")
                return
            
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
                colour = Colour.default()

            else:
                text = f"Successfully Added Assignment with key `{ ret }`" if type_ == 'add' \
                else "Successfully Edited Assignment."
                colour = Colour.teal()
                log.debug(f'{ctx.author.id} add/edit new assignment and passed in successfully.')

            await self.close(ctx, text, colour)
            return

        elif emoji == "1️⃣":
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

    async def adding(self, ctx: Context) -> None:
        """
        A method that will get an input from target message, and delete it.
        """
        while self.tasks[ctx.author.id]["details"]["state"] != 0:
            try:
                message = await self.bot.wait_for_message(ctx, timeout = 300)
            except: # Timeout, or something went wrong.
                await self.close(ctx)
                return
            content = message.content

            """
            Checks:
                * Message content is not bot command.
                * User has menu opened.
                * State of menu needs to be valid.
            """
            if ctx.author.id not in self.tasks or \
            self.tasks[ctx.author.id]['details']['state'] == 0:
                return
            
            if content is not None and content.startswith(self.bot.command_prefix): return
            
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
                self.tasks[ctx.author.id]["details"]["headers"]["date"] = content
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
            if ctx.author.id in self.tasks:
                await message.delete()
                await self.update_embed(ctx)

    @command(hidden=True)
    async def school(self, ctx: Context) -> None:
        if random.randint(1, 1000) == 1:
            await ctx.send("Sucks")
        else:
            await ctx.send("Good place.")


def setup(bot: Bot) -> None:
    bot.add_cog(Assignments(bot))