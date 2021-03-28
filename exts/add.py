from discord.ext.commands import Cog, Context, command
from discord import Embed, Colour, RawReactionActionEvent
from bot import Bot
from utils import planner

import logging
import traceback
from asyncio import sleep

TITLES = {
    "title": ("{} Title", 1), 
    "description": ("{} Description", 2), 
    "date": ("{} Date", 3), 
    "image": ("{} Image", 4)
}

EMOJI_STRING = (":one:", ":two:", ":three:", ":four:", ":arrow_left: ")
EMOJIS = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "✅", "❎")

log = logging.getLogger(__name__)

class Adder(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.tasks = {}
    
    @staticmethod
    def close_embed(reason: str) -> Embed:
        log.debug("Close embed requested")
        embed = Embed(colour = Colour.blue())
        embed.title = "[Closed Menu]" if reason is None else reason
        log.debug("Returned Close Embed")
        return embed
    
    @staticmethod
    def get_title_from_key(key: str, state: int) -> str:
        log.debug("GETTING title from key")
        title, crrent = TITLES[key]
        title = title.format(EMOJI_STRING[crrent-1])
        log.debug("Got title from key")
        return f"{title} {EMOJI_STRING[4]*3}" if crrent == state else title


    def base_embed(self, ctx: Context) -> Embed:
        log.debug("Creating Base embed")
        embed = Embed(
            description = "Click the reaction to select and edit.",
            colour = Colour.teal(),
            timestamp = ctx.message.created_at
        )
        embed.set_author(name = "Homework Menu", icon_url = ctx.author.avatar_url)
        embed.set_footer(text = "Send message to edit/input data.")
        details = self.tasks[ctx.author.id]["details"]
        header = details["headers"]
        state = details["state"]
        
        for n in header:
            log.debug(f"Adding field, {n}")
            name = self.get_title_from_key(n, state)    
            value = planner.get_readable_date(header[n])

            embed.add_field(name=name, value=value, inline=False)
        
        if details["image"] != "Not Attached":
            log.debug("No Image Attached")
            embed.set_image(url=details["image"])
        else:
            log.debug("Image Attached")
            embed.add_field(name=self.get_title_from_key("image", state), value = details["image"], inline=False)        

        return embed
    
    async def update_embed(self, ctx: Context) -> None:
        log.debug("Updating Embed")
        message = self.tasks[ctx.author.id]["info"]["message"]
        if message is None:
            return

        if self.tasks[ctx.author.id]["details"]["state"] == 0:
            await self.close(ctx)
            return
        
        embed = self.base_embed(ctx)        
        await message.edit(embed=embed)  
        log.debug("Updated Success") 
    
    async def close(self, ctx: Context, reason: str = None) -> None:
        if ctx.author.id not in self.tasks:
            return
        log.debug("Closing Embed")
        message = self.tasks[ctx.author.id]["info"]["message"]
        await message.edit(embed=self.close_embed(reason))         
        try:
            await message.clear_reactions()
        except:
            pass       
        
        await sleep(2)        
        
        if ctx.author.id in self.tasks:
            del self.tasks[ctx.author.id]
            log.debug("Removed from tasks")
    
    @command(name="addv2")
    async def add(self, ctx: Context) -> None:
        if ctx.author.id in self.tasks:
            await ctx.send(":x: **Please wait a bit before doing this.**")
            return
        
        self.tasks[ctx.author.id] = {
            "details":{
                "state": 1,
                "image": "Not Attached",
                "headers":{
                    "title": "Untitled",
                    "description": "No Description Provied",
                    "date": "Unknown",
                }
            },
            "info":{                
                "ctx": ctx,
                "message": None
            }
        }

        embed = self.base_embed(ctx)
        message = await ctx.send(embed=embed)
        self.tasks[ctx.author.id]["info"]["message"] = message
        log.debug("Inituallizing Data")
        await self.bot.add_reactions(message, EMOJIS)
        log.debug("Continue adding")
        await self.adding(ctx)
    
    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        await self.process_reaction_event(payload)
    
    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent) -> None:
        await self.process_reaction_event(payload)
    
    async def process_reaction_event(self, payload: RawReactionActionEvent) -> None: 
        emoji = str(payload.emoji)
        
        if emoji not in EMOJIS or payload.user_id not in self.tasks:
            return
        
        log.debug("Processing Emoji")

        ctx = self.tasks[payload.user_id]["info"]["ctx"]
        old_state = self.tasks[payload.user_id]["details"]["state"]

        if emoji == "❎":
            await self.close(ctx)
            return
        
        elif emoji == "✅":

            try:
                ret = await planner.add(
                    ctx.guild.id, # Required Args
                    title = self.tasks[ctx.author.id]["details"]["headers"]["title"], # kwargs
                    description = self.tasks[ctx.author.id]["details"]["headers"]["description"],
                    date = self.tasks[ctx.author.id]["details"]["headers"]["date"],
                    image_url = self.tasks[ctx.author.id]["details"]["image"],
                )
                
            except Exception:
                text = "Unable to add Assignment, Problem has been reported."
                await self.bot.log(__name__, f"An Exception were found while finishing adding assignment\n```py\n{traceback.format_exc()}\n```", True)

            else:
                text = f"Successfully Added Assignment with key `{ ret }`"
                await self.bot.log(__name__, f"New Assignment has been added on Guild {payload.guild_id} with key `{ret}`")

            await self.close(ctx, text)
            return
        
        elif emoji == "1️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 1
        elif emoji == "2️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 2
        elif emoji == "3️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 3
        elif emoji == "4️⃣":
            self.tasks[payload.user_id]["details"]["state"] = 4    
        else:
            return
        
        if old_state != self.tasks[payload.user_id]["details"]["state"]:
            await self.update_embed(ctx)
        return

    async def adding(self, ctx: Context) -> None:

        while ctx.author.id in self.tasks:
            try:
                log.debug("waiting for message")
                message = await self.bot.wait_for_message(ctx, timeout = 60)
            except:
                log.debug("too slow!")
                await self.close(ctx)
                return
            content = message.content
            if content.startswith(self.bot.command_prefix):
                return
            if ctx.author.id not in self.tasks:
                continue
            
            log.debug("processing new message")

            state = self.tasks[ctx.author.id]["details"]["state"]
            if state == 1:
                self.tasks[ctx.author.id]["details"]["headers"]["title"] = content
            elif state == 2:
                self.tasks[ctx.author.id]["details"]["headers"]["description"] = content
            elif state == 3:
                self.tasks[ctx.author.id]["details"]["headers"]["date"] = content
            elif state == 4:
                if len(message.attachments) < 1:
                    log.debug("No image Attached in adding")
                    continue
                else:
                    log.debug("an Image Attached in adding")
                    image = message.attachments[0]

                    image_url = await self.bot.get_image_url(image)
                    self.tasks[ctx.author.id]["details"]["image"] = image_url
            
            self.tasks[ctx.author.id]["details"]["state"] = state + 1 if state < 4 else 1
            log.debug("Changed state")
            if ctx.author.id in self.tasks:
                await message.delete()
                log.debug("deleted message")
                await self.update_embed(ctx)
                log.debug("updated embed from adding")


def setup(bot: Bot) -> None:
    bot.add_cog(Adder(bot))