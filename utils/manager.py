"""
Bot Work channel Manager, to keep track all channels across guilds.
Made by Tpmonkey
"""

import logging
log = logging.getLogger(__name__)

class Manager:
    def __init__(self, bot):
        self.bot = bot
        self.__data = bot.database.loads("GUILD")

    def create_guild(self, guild_id: int) -> bool:
        """
        Create a new guild data and store it into database.
        Only works if guild is not existed.
        """
        if str(guild_id) not in self.__data:
            self.__data[str(guild_id)] = {}
            self.save()
            log.debug(f'created new guild {guild_id}')
            return True        
        return False

    def check(self, guild_id: int) -> bool:
        """ Check if Work Channels in targeted guild valid or not. """
        # If the guild is not exist, there no need to check any further.
        if self.create_guild(guild_id):
            return False
        
        d = self.__data[str(guild_id)]
        try: # Get the ID if possible
            a = d['active']
            p = d['passed']
        except KeyError:
            return False
        
        # Get the channels.
        return False if self.bot.get_channel(a) is None or self.bot.get_channel(p) is None else True
    
    def get_all_guild(self) -> list:
        """ Get all Guilds ID in system. """
        return [int(i) for i in self.__data]
    
    def delete(self, guild_id: int) -> bool:
        try: del self.__data[str(guild_id)]
        except KeyError:
            log.warning(f'no valid guild called "{guild_id}"')
            return False
        else:
            log.debug(f'deleted guild {guild_id} from system')
            self.save()
            return True

    def get_all(self) -> dict:
        """ Get all Guilds Channels Data. """
        return self.__data

    def get(self, guild_id: int) -> dict:
        """ Get Guild Work Channels ID from Guild ID. """
        try:
            return self.__data[str(guild_id)]
        except KeyError:
            return {}       

    def set(self, guild_id: int, type_: str, channel_id: int) -> None:
        """ Set Work Channel ID into targeted Guild. """
        self.create_guild(guild_id)
        self.__data[str(guild_id)][type_] = channel_id
        
        self.save()

    def save(self) -> None:
        """ Save all data. """
        self.bot.database.dumps("GUILD", self.__data)