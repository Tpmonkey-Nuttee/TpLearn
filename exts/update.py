# Update Works system.
# Made by Tpmonkey

from discord.ext.commands import Cog, Context, command, is_owner
from discord.ext.tasks import loop
from discord import Message, TextChannel

import config
from bot import Bot

import traceback
import asyncio

MINUTES = config.update_work_cooldown

class Updater(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.updating = False
        self.loop.start()
    
    def check(self, message: Message, **work: dict) -> bool:
        """Check if the bot should update works embed or not to prevent rate limit."""
        if len(message.embeds) == 0: return False
        
        embed = message.embeds[0].to_dict()
        footer = embed['footer']['text']
        title = embed['author']['name']
        colour_embed = embed['color']
        colour = self.bot.get_colour(work.get('date')).value
        title_ = self.bot.get_title(work.get('title'), work.get('date'))

        return footer[-8:] == work.get('key') and colour_embed == colour and title == title_

    @loop(minutes = MINUTES)
    async def loop(self) -> None:
        await self.bot.wait_until_ready()

        # We need to check if the bot already updating or not.
        if not self.updating: await self.update()

    async def get_messages(self, channel: TextChannel) -> list:
        """Get messages from active-works channel, Wil only get its own messages."""
        messages = []
        async for message in channel.history(limit=30):
            if message.author.id == self.bot.user.id: messages.append(message)
            
        return messages
    
    async def update(self) -> None:
        self.updating = True

        data = self.bot.manager.main_data

        for gid in data:
            # Check if the channel valid or not.
            if not self.bot.manager.check(gid): continue
            
            works = self.bot.planner.get_sorted(gid)
            try: ret = await self.update_active(works, data[gid])
            except:
                await self.bot.log(__name__, 
                    f":negative_squared_cross_mark: Unable to update works at {gid} with error: \n{traceback.format_exc()}")
            else:
                if len(ret) != 2:
                    await self.bot.log(__name__,
                        f":white_check_mark: Sucessfully update works at {gid} :\n" \
                        ", ".join(ret))

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
        if channel is None: return

        messages = await self.get_messages(channel)

        cw = len(works)
        cm = len(messages)

        # To use for logging.
        messages_output = ["Tw `{}`".format(cw), "Tm `{}`".format(cm)]

        if cw < cm: # Case 1
            for index, message in enumerate(messages):
                try:
                    work = works[index]
                    embed = self.bot.get_embed(**works[index])
                except IndexError: # Ran out of works.
                    await message.delete()
                    messages_output.append("`D` w<m")
                else:
                    if self.check(message, **work) and not bypass: continue

                    await message.edit(embed=embed)
                    messages_output.append("`E` w<m")
                
                # Wait a bit before doing next operation.
                await asyncio.sleep(1)

        elif cw > cm: # Case 2
            messages.reverse()
            works.reverse()
            for index, work in enumerate(works):        
                embed = self.bot.get_embed(**work)
                try:
                    message = messages[index]                    
                except IndexError: # Ran out of embeds to edit.
                    await channel.send(embed=embed)
                    messages_output.append("`S` w>m")
                else:
                    if self.check(message, **work) and not bypass: continue
                    
                    await messages[index].edit(embed=embed) 
                    messages_output.append("`E` w>m")
                
                # Wait a bit before doing next operation.
                await asyncio.sleep(1)
        
        else:
            for message, work in zip(messages, works):
                if self.check(message, **work) and not bypass: continue
                
                embed = self.bot.get_embed(**work)
                await message.edit(embed=embed)
                messages_output.append("`E` w=m")

                # Wait a bit before doing next operation.
                await asyncio.sleep(1)
        
        return messages_output

    @command(name='update')
    @is_owner()
    async def _update(self, ctx: Context, gid: str, bypass: bool = False) -> None:
        """Force update command, can be bypass system."""
        if self.updating and not bypass:
            await ctx.send(
                "The bot currently updating data, Please try again later.\nPlease keep in mind that, bypassing the system will may result in bot getting rate limited.")
            return
        
        m = await ctx.send("Trying to update...")
        d = self.bot.manager.main_data
        works = self.bot.planner.get_sorted(gid)

        try: result = await self.update_active(works, d[gid], True)
        except:
            await self.bot.log(__name__, f"Unable to update works at {gid} with error: {traceback.format_exc()}")
            content = "Update failed, Exception in logs."
        else: content = "\n".join(result)

        await m.edit(content=content)


def setup(bot: Bot) -> None:
    bot.add_cog(Updater(bot))