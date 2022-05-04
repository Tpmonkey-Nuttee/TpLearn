"""
Bot Patch checker, Monitoring Version Change and Patch Notes.
Used for logging and moderating.
Made by Tpmonkey
"""

from discord.ext.commands import Cog
from discord import Embed, Colour

from bot import Bot

from datetime import datetime
import logging

log = logging.getLogger(__name__)

class NewPatch(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @Cog.listener()
    async def on_connect(self) -> None:
        await self.check()
    
    @Cog.listener()
    async def on_resumed(self) -> None:
        await self.check()

    async def check(self) -> None:
        await self.bot.wait_until_ready()

        current_version = await self.bot.database.load("VERSION")
        if current_version is None:
            log.debug("Couldn't load bot version from database, ignoring...")
            return
        
        system_version = self.bot.config.version

        if current_version != system_version:
            log.debug("Version change found, annoucing..")
            await self.push_version_change(current_version, system_version)
            await self.bot.database.dump("VERSION", system_version)
    
    async def push_version_change(self, old_version: int, new_version: int) -> None:
        embed = Embed(
            title = "Version Change Detected",
            colour = Colour.teal(),
            timestamp = datetime.utcnow()
        )

        patch_notes = "\n".join(self.bot.config.note) if len(self.bot.config.note) != 0 else "No patch note were found."

        embed.description = "Version **{}** → **{}**".format(old_version, new_version)        
        embed.add_field(name = "Patch Note:", value=patch_notes)
        
        await self.bot.get_channel(762326316455821363).send(embed=embed)
        await self.bot.get_channel(889196845090365491).send(embed=embed)

def setup(bot: Bot) -> None:
    bot.add_cog(NewPatch(bot))