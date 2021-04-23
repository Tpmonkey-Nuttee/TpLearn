# A Bot Works Channels Manager.
# Made by Tpmonkey

import logging
log = logging.getLogger(__name__)

class Manager:
    def __init__(self, bot):
        self.bot = bot
        self.main_data = bot.database.loads("GUILD")

    def create_guild(self, guild_id: int) -> bool:
        """
        Create a new guild data and store it into database.
        Only works if guild is not existed.
        """

        if str(guild_id) not in self.main_data:
            self.main_data[str(guild_id)] = {}
            self.save()
            return True
        
        return False

    def check(self, guild_id) -> bool:
        """
        Check if Work Channels in targeted guild valid or not.    
        """
        # If the guild is not exist, there no need to check any further.
        if self.create_guild(guild_id):
            return False
        
        d = self.main_data[str(guild_id)]
        try: # Get the ID if possible
            a = d['active']
            p = d['passed']
        except:
            return False
        
        # Get the channels.
        if self.bot.get_channel(a) is None or self.bot.get_channel(p) is None:
            return False
        return True

    def get_all(self) -> dict:
        """
        Get all Guilds Channels Data.
        """
        return self.main_data

    def get(self, guild_id: int) -> dict:
        """
        Get Guild Work Channels ID from Guild ID.
        """
        self.create_guild(guild_id)
        return self.main_data[str(guild_id)]

    def set(self, guild_id: int, type_: str, channel_id: int) -> None:
        """
        Set Work Channel ID into targeted Guild.
        """
        self.create_guild(guild_id)

        self.main_data[str(guild_id)][type_] = channel_id
        self.save()

    def save(self) -> None:
        """
        Save all data.
        """
        self.bot.database.dumps("GUILD", self.main_data)