"""
WaitFor Utils command.

An extension from TpBot
"""

from discord.ext.commands import Cog, Context, command, is_owner
from discord import User, Message, TextChannel, Member, VoiceState

from bot import Bot

from typing import Union
import datetime

ALLOWED_EVENT = ("on_message", "on_status", "on_typing", "on_voicechat")

class WaitForEvent(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.task = {}
        self.ctx = None
    
    @command(hidden=True)
    @is_owner()
    async def waitfor(self, ctx: Context, user: User, event: str) -> None:
        """
        Wait For Event (Bot is not included)

        Events:
        on_message: On New Message or Edit message
        on_status: On Status Change
        on_typing: On User start typing
        on_voicechat: On VoiceChat channel update (join, leave, change)
        """
        if event not in ALLOWED_EVENT:
            await ctx.send(f"No event name: {event}\nAllowed Event: {', '.join(ALLOWED_EVENT)}")
            return
        
        self.task[event] = user.id
        if self.ctx is None: self.ctx = ctx

        await ctx.send("Event Added")
    
    @command(hidden=True)
    @is_owner()
    async def remove_waitfor(self, ctx: Context, event: str) -> None:
        try:
            del self.task[event]
        except:
            await ctx.send("Event not found.")
        await ctx.send("Removed Event.")
    
    async def event_trigger(self, event: str, message: str) -> None:
        # del self.task[event]

        await self.ctx.send(f"{event}: {message}")
    
    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot: return
        if "on_message" not in self.task:
            return
        
        if message.author.id == self.task['on_message']:
            await self.event_trigger(
                'on_message', 
                f'{message.author} has sent a message in {message.channel.mention} [{datetime.datetime.now()}]'
            )
    
    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message) -> None:
        if before.author.bot: return
        if "on_message" not in self.task:
            return
        
        if before.author.id == self.task['on_message']:
            await self.event_trigger(
                'on_message', 
                f"{before.author} edited message in {before.channel.mention} \nfrom {before.content} to {after.content} [{datetime.datetime.now()}]"
            )

    @Cog.listener()
    async def on_typing(self, channel: TextChannel, user: Union[Member, User], when: datetime.datetime) -> None:
        if user.bot: return
        if "on_typing" not in self.task:
            return
        
        if user.id == self.task['on_typing']:
            await self.event_trigger(
                'on_typing',
                f"{user} is typing in {channel.mention} [{when}]"
            )
    
    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        if before.bot: return
        if "on_status" not in self.task:
            return
        
        if before.id == self.task['on_status']:
            if before.mobile_status != after.mobile_status or \
            before.desktop_status != after.desktop_status or \
            before.web_status != after.web_status:
                
                await self.event_trigger(
                    'on_status',
                    f"{before} changed status \nFrom Mobile: {before.mobile_status} Desktop: {before.desktop_status} WebPage: {before.web_status} "
                    f"\nTo Mobile: {after.mobile_status} Desktop: {after.desktop_status} WebPage: {after.web_status}\n[{datetime.datetime.now()}]"
                )
    
    @Cog.listener()
    async def on_voice_state_update(self, user: Member, before: VoiceState, after: VoiceState) -> None:
        if user.bot: return
        if "on_voicechat" not in self.task:
            return

        if user.id == self.task['on_voicechat'] and before.channel != after.channel:
            await self.event_trigger(
                'on_voicechat',
                f'{user} updated VoiceState from {before.channel} to {after.channel} in {user.guild} [{datetime.datetime.now()}]'
            )



def setup(bot: Bot) -> None:
    bot.add_cog(WaitForEvent(bot))