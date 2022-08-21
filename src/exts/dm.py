"""
Bot DM Manager.
Made by Tpmonkey
"""

from discord import Message, Embed, Colour, User
from discord.ext.commands import Cog, Context, command, is_owner

from bot import Bot

class VoiceChannel(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel = None
    
    @Cog.listener()
    async def on_ready(self) -> None:
        """ Get Bot's DM-Channel. """
        self.channel = self.bot.get_channel(self.bot.config.dm_channel_id)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """ Listening for DM. """
        if not self.channel: 
            self.channel = self.bot.get_channel(self.bot.config.dm_channel_id)

        # RULES/CHECKS
        # - Author must not be a bot or owner.
        # - Guild needs to be None, that means It's on Bot DM or GROUP.

        if message.author.bot or message.author.id == self.bot.owner_id or message.guild != None:
            return
        
        user = message.author

        # Create an Embed
        embed = Embed(colour=Colour.blue())
        embed.set_author(name= f"New message from {user}#{user.discriminator}", icon_url = user.avatar.url)
        embed.description = user.id # You can hold down an embed in phone, and It will copy description
        embed.add_field(name = "Message:", value = message.content)

        await self.channel.send(embed=embed) # Send to mod channel
    
    @command(name = "reply", aliases = ("r", ))
    @is_owner()
    async def reply(self, ctx: Context, user: User, *, message: str):
        """ Reply message to User DM. """
        
        # Send the message
        await user.send(message)

        # Send back to mod channel
        embed = Embed(colour=Colour.dark_red())
        embed.set_author(name= f"Replied to {user}", icon_url = ctx.author.avatar.url)
        embed.description = user.id
        embed.add_field(name = "Message:", value= message)

        await ctx.send(embed=embed)

        # Delete the comamnd message when It's done.
        await ctx.message.delete()

def setup(bot: Bot) -> None:
    bot.add_cog(VoiceChannel(bot))