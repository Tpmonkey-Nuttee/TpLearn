"""
Bot's Active-Works Updater.
Made by Tpmonkey
"""

from discord.ext.tasks import loop
from discord import Message, TextChannel
from discord.ext.commands import Cog, Context, command, is_owner

import config
from bot import Bot

import time
import logging
import asyncio
import traceback
from datetime import datetime

log = logging.getLogger(__name__)
MINUTES = config.update_work_cooldown

class Updater(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.last_check['update'] = {}

        self.updating = False
        self.loop.start()
    
    def cog_unload(self):
        self.loop.cancel()
    
    @Cog.listener()
    async def on_resumed(self) -> None:
        """
        Check if loop running correctly.
        """
        if not self.loop.is_running():
            self.loop.restart()
            await self.bot.log(__name__, "Updater Loop is not running, Restarted", True)
            await self.bot.log(__name__, traceback.format_exc())          
    
    def check(self, message: Message, **work: dict) -> bool:
        """
        Check if the bot should update works embed or not to prevent rate limit.
        Return True: The same embed, don't update it
        Return False: Something is difference, Update it.
        """
        if len(message.embeds) == 0: # Normal message with no embed
            return False
        
        # Get first embed.
        embed = message.embeds[0].to_dict()

        # Check assignment Key
        key_embed = embed.get('description')        
        key = work.get('key')

        # Assignment Colour
        colour_embed = embed.get('color')
        colour = self.bot.get_colour(work.get('date')).value

        # Check title.
        title_embed = embed.get('author', {}).get('name')
        title = self.bot.get_title(
            work.get('title'), work.get('date'), 
            passed=work.get("already_passed"), lasted=work.get("lasted", 1)
        )

        # Check description
        try:
            desc_embed = embed['fields'][1]['value']
        except (IndexError, KeyError):
            desc_embed = "No Description Provided"
        desc = work.get('desc')

        # False if needed update, True if doesn't need an update
        try: 
            image_embed = embed['image']['url'] 
        except KeyError:
            image_embed = "Not Attached"
        image = work.get("image-url")        

        return (
            key_embed == key and colour_embed == colour and title_embed == title and desc_embed == desc and image_embed == image
        )

    @loop(minutes = MINUTES)
    async def loop(self) -> None:
        await self.bot.wait_until_ready()

        # We need to check if the bot already updating or not.
        if not self.updating: 
            await self.update()
        else: 
            await self.bot.log(__name__, "Cannot keep up with update work system. Some Guild maybe affected.")

    async def get_messages(self, channel: TextChannel) -> list:
        """Get messages from active-works channel, Wil only get its own messages."""
        messages = []

        async for message in channel.history(limit=30):
            if message.author.id == self.bot.user.id: 
                messages.append(message)
            
        return messages
    
    async def update(self) -> None:
        # Disable function until It's completed
        self.updating = True
        # Time took for debugging
        _s_ = time.time()

        # Get data
        data = self.bot.manager.get_all()
        need_update = self.bot.planner.need_update
        log_msg = ""

        for gid in need_update:
            # Check if the channel valid or not.
            if not self.bot.manager.check(gid): 
                continue
            
            self.bot.last_check['update'][gid] = datetime.utcnow()
            works = self.bot.planner.get_sorted(gid)

            try: 
                ret = await self.update_active(works, data[gid])
            except Exception: 
                log_msg += f"[x] {gid}: {traceback.format_exc(limit = -1)}\n"
                
            else:
                if len(ret) != 2: 
                    log_msg += f"[/] {gid}: {''.join(ret)}\n"

    
        if log_msg:
            await self.bot.log(__name__, log_msg)

        # If Actually updated something, log it
        if len(need_update) > 0 and time.time() - _s_ > 30: 
            await self.bot.log(__name__, f"Time took to update all works: {time.time() - _s_}s")

        # Enable this function again
        self.updating = False
    
    async def update_active(self, works: list, channels: dict, bypass: bool = False) -> list:  
        """
        Update active-works embed(s).
        
        To update active-works channel, We need to check a lot of things to prevent bot for getting rate limit.
        These are the concept.
        
        * Case 1: Amount of Works is less than Embeds in active-works channel.
            - Edit embeds and delete overhanging embeds.
        * Case 2: Amount of Works is more than Embeds in active-works channel.
            - Edit embeds and send overhanging works.
        * Case 3: Amount of Work is equal to Embeds.
            - Edit embeds only.

        But, If the embeds has nothing new, pass it.
        You can also bypass the function, for debugging.
        """
        
        channel = self.bot.get_channel(channels['active'])
        if channel is None: 
            return

        messages = await self.get_messages(channel)

        cw = len(works)
        cm = len(messages)

        # To use for logging.
        messages_output = ["{}".format(cw), "{}".format(cm)]

        if cw < cm: # Case 1
            for index, message in enumerate(messages):
                try:
                    work = works[index]                    
                except IndexError: # Ran out of works.
                    await message.delete()
                    messages_output.append("D")
                else:
                    if self.check(message, **work) and not bypass: 
                        continue

                    embed = self.bot.get_embed(**works[index])
                    await message.edit(embed=embed)
                    messages_output.append("E")
                
                # Wait a bit before doing next operation.
                await asyncio.sleep(3)

        elif cw > cm: # Case 2
            messages.reverse()
            works.reverse()
            for index, work in enumerate(works):        
                embed = self.bot.get_embed(**work)
                try: 
                    message = messages[index]                    
                except IndexError: # Ran out of embeds to edit.
                    await channel.send(embed=embed)
                    messages_output.append("S")
                else:
                    if self.check(message, **work) and not bypass: 
                        continue
                    
                    await messages[index].edit(embed=embed) 
                    messages_output.append("E")
                
                # Wait a bit before doing next operation.
                await asyncio.sleep(3)
        
        else:
            for message, work in zip(messages, works):
                if self.check(message, **work) and not bypass: 
                    continue
                
                embed = self.bot.get_embed(**work)
                await message.edit(embed=embed)
                messages_output.append("E")

                # Wait a bit before doing next operation.
                await asyncio.sleep(3)
        
        return messages_output

    @command(name='fupdate')
    @is_owner()
    async def _update(self, ctx: Context, gid: str, bypass: bool = False) -> None:
        """Force update command, can be bypass system."""
        if self.updating and not bypass:
            return await ctx.send(
                "The bot currently updating data, Please try again later.\nPlease keep in mind that, bypassing the system will may result in bot getting rate limited."
            )
        
        m = await ctx.send("Trying to update...")
        d = self.bot.manager.get_all()
        works = self.bot.planner.get_sorted(gid)

        result = await self.update_active(works, d[gid], True)
        content = "\n".join(result)

        await m.edit(content=content)
    
    @command(hidden=True)
    async def hide(self, ctx: Context) -> None:
        await ctx.send("Yes, I'm hiding... Don't tell anyone! :shushing_face:")


def setup(bot: Bot) -> None:
    bot.add_cog(Updater(bot))