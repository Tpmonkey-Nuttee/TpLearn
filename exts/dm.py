# Bot direct message manager
# Made by Tpmonkey

from discord.ext.commands import Cog, Context, command, is_owner
from discord import Message, Embed, Colour

from bot import Bot

class VoiceChannel(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel = None
    
    @Cog.listener()
    async def on_ready(self) -> None:
        self.channel = self.bot.get_channel(self.bot.config.dm_channel_id)
        self.me = self.bot.get_user(self.bot.owner_id)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        # Listening for dm.
        if not self.channel:
            self.channel = self.bot.get_channel(self.bot.config.dm_channel_id)
        if message.author.bot or message.author.id == self.bot.owner_id or message.guild != None:
            return
        
        user = message.author

        embed = Embed(colour=Colour.blue())
        embed.set_author(name= f"New message from {user}", icon_url = user.avatar_url)
        embed.description = user.id
        embed.add_field(name = "Message:", value = message.content)

        await self.channel.send(embed=embed)

    
    @command(name = "reply", aliases = ("r", ))
    @is_owner()
    async def reply(self, ctx: Context, user_id: int, *, message: str):
        user = self.bot.get_user(user_id)
        if not user:
            await ctx.send(":x: Unable to get User Object from the API!")
            return
        
        await user.send(message)
        embed = Embed(colour=Colour.dark_red())
        embed.set_author(name= f"Replied to {user}", icon_url = ctx.author.avatar_url)
        embed.description = user.id
        embed.add_field(name = "Message:", value= message)

        await ctx.send(embed=embed)
        await ctx.message.delete()

def setup(bot: Bot) -> None:
    bot.add_cog(VoiceChannel(bot))