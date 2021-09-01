from discord.ext.commands import Cog
from discord import Message, Embed

from bot import Bot

GUILD_ID = 773426467492069386
MY_ID = 518063131096907813
RYU_ID = 584005308037464089
CHANNEL_ID = 856555706752827462

class AntyPing(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel = None

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        if self.channel is None: self.channel = self.bot.get_channel(CHANNEL_ID)

        if message.guild is None: return
        if message.guild.id != GUILD_ID: return
        
        if str(MY_ID) in message.content: 
            await message.delete()
            await self.channel.send(
                f"{message.author} tried to ping you with message content:", 
                embed = Embed(
                    title="content", 
                    description = message.content.replace(str(MY_ID), "MyName")
                    )
                )

def setup(bot: Bot) -> None:
    bot.add_cog(AntyPing(bot))