"""
An Assignment Manager.
Add, Remove, Keep track of all assignments.
Made by Tpmonkey
"""

from typing import Optional
import datetime
import secrets
import discord
import random
import time

from utils.time import today_th

import logging
log = logging.getLogger(__name__)

class Planner:
    def __init__(self, bot):
        self.bot = bot
        self.__data = dict(bot.database.loads("WORKS", {}))
        self.__need_update = []
        self.trigger_update()
    
    @property
    def need_update(self) -> list:
        """ Return Guild IDs that need an update. """
        # Remove duplicate ID.
        p = list( dict.fromkeys( [str(i) for i in self.__need_update] ) )
        # Update value, In this case It should be reset to empty list.
        self.__need_update = [] # [str(i) for i in self.__need_update if str(i) not in p]
        return p
    
    def trigger_update(self) -> None:
        log.debug(f'triggered update')
        self.__need_update = self.get_all_guild()

    def get_number_all(self) -> int:
        """
        Get count of all available works.
        """
        amount = 0
        for i in self.__data:
            amount += len(self.get_all(i))
        return amount

    def get_all(self, guild_id: int) -> list:
        """
        Get all the assignments that exist and still valid from targeted Guild ID.
        """
        guild_id = str(guild_id)
        if guild_id not in self.__data:
            return []

        d = []
        for i in self.__data[guild_id]:
            if self.__data[guild_id][i]['already-passed']: 
                # Ignore passed assignment.
                continue

            d.append(self.__data[guild_id][i])

        return d
    
    def get_number_all_passed(self, guild_id: int) -> int:
        """
        Get amount the assignments that is invalid from targeted Guild ID.
        """
        guild_id = str(guild_id)
        if guild_id not in self.__data:
            return 0
        
        d = 0
        for i in self.__data[guild_id]:
            if self.__data[guild_id][i]['already-passed']: 
                d += 1            

        return d

    def get(self, guild_id: int, key: str) -> dict:
        """
        Get an Assignment base on key from targeted Guild ID.
        """
        guild_id = str(guild_id)
        if guild_id not in self.__data:
            return {}

        return self.__data[guild_id][key]

    def get_all_guild(self) -> list:
        """
        Get all Guild IDs.
        """
        return [int(key) for key in self.__data]

    def get_sorted(self, guild_id: int) -> list:
        """
        Get sorted assignment base on date of targeted Guild ID.
        The undefined date will be in front of defined date.
        """
        data = self.get_all(guild_id)
        dates = list()
        unknown_date = list()

        # Convert it to datetime type first, using readable date that it has.
        for ts in data:
            if self.strp_able(ts['readable-date']):
                dates.append(datetime.datetime.strptime(ts['readable-date'], "%A %d %B %Y"))
            else:
                unknown_date.append(ts)

        # Sort it
        dates.sort()
        # now convert it back
        sorteddates = [datetime.datetime.strftime(ts, "%A %d %B %Y") for ts in dates]

        # Make a list of all the date
        # All the data will be in one list in dict type
        final = []
        for i in sorteddates:
            keys = [i.get('key') for i in final]
            for j in data:
                if j['readable-date'] == i and j['key'] not in keys:
                    final.append(j)
        
        # Unknown date should be in front of the Known date.
        log.debug(f'returning sorted date for {guild_id}')
        return unknown_date + final
    
    def get_embed(self, guild_id: int) -> discord.Embed:
        """
        Embed contained a List of all works in that targeted guild.
        """
        t = time.perf_counter()
        if len(self.get_all(guild_id)) == 0:
            log.debug(f'getting embed return nothing for {guild_id}')
            return discord.Embed(
                title = "Congratuation! :heart:",
                description = "Looks like You don't have any assignment!",
                colour = discord.Colour.blue(),
                timestamp = datetime.datetime.utcnow()
            ).set_footer(text = "Use add command to add one!")
        
        print("First check", time.perf_counter() - t)
        
        _sorted = self.get_sorted(guild_id)
        formatted = {}
        # Idk why, but I wanted the 'formatted' dict to be
        # {
        #   "date that human can read": ["assignment key 1", "assignment key 2"]
        # }

        for value in _sorted:
            date_key = self.try_strp_date( value['date'] ).strftime("%d-%m-%Y") if self.strp_able( value['readable-date'] ) else "Unknown Date"

            if date_key not in formatted:
                formatted[date_key] = [ value["key"] ]
            else:
                formatted[date_key].append(value["key"])
        
        print("Second sort", time.perf_counter() - t)
        
        # Let's create base Embed.
        embed = discord.Embed()
        embed.title = "Upcoming Assignment" if len(_sorted) == 1 else "Upcoming Assignments"
        embed.title = ":calendar_spiral: " + embed.title + " :calendar_spiral:"
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text = "Take a look at #active-works channel for more info!")
        embed.description = random.choice( self.bot.config.facts )

        closest_day = None

        for date in formatted:   
            # Create Field Name
            if date == "Unknown Date": 
                name = date
            else:
                name = self.bot.get_title(self.get_readable_date(date), date)

            # Create Field Value
            value = ""
            for key in formatted[date]: 
                value += f"↳`{key}` • { self.get(guild_id, key)['title'] }\n"

            if len(value) >= 1024: 
                value = value[:1020] + "..." # Embed Field Value cannot be longer than 1024 letters

            # Add Field
            embed.add_field(name=name, value=value, inline = False)

            # Track the closest day and use for Embed Colour
            in_days = self.bot.in_days(date)
            if in_days is None: 
                continue            
            elif closest_day is None or in_days < closest_day: 
                closest_day = in_days
        
        print("last loop", time.perf_counter() - t)
        
        embed.colour = self.bot.get_colour(gap=closest_day)
        log.debug(f'return embed for {guild_id}')
        
        log.debug(f"took {time.perf_counter() - t} second for {guild_id}")
        return embed

    def check_valid_key(self, guild_id: int, key: str) -> bool:
        """
        Check if a Assignment key valid on targeted Guild ID or not.
        """
        return self.__data.get(str(guild_id), {}).get(key, None) is not None

    async def add(self, guild_id: int, **kwargs) -> str:
        """
        Add an Assignment to the targeted Guild ID.
        Need to provide all Assignment Attribute.
        """

        self._create_if_nexist(guild_id)
        title = kwargs.get("title", "Untitled")
        description = kwargs.get("description", "No Description Provided")
        date = kwargs.get("date", "Unknown")
        image_url = kwargs.get("image_url")
        key = kwargs.get('key') or self.generate_key()

        date_tracker = today_th(True).strftime("%d-%m-%Y") if self.try_strp_date(date) is None else date

        self.__data[str(guild_id)][key] = {
            "title": title,
            "desc": description,
            "date": date,
            "image-url": image_url,
            "readable-date": self.get_readable_date(date),
            "already-passed": False,
            "date-tracker": date_tracker,
            "key": key
        }

        log.debug("added Assignment from `{}` with key `{}`".format(guild_id, key))
        self._save() # don't forget to save!
        self.__need_update.append(guild_id)
        
        return key

    async def remove(self, guild_id: int, key: str) -> Optional[dict]:
        """
        Remove an Assignment base on key from targeted Guild ID.
        """
        if self._create_if_nexist(guild_id):
            return 
        
        # Add key to the dict before sending back.
        data = self.__data[str(guild_id)][key]
        data["key"] = key 

        log.trace("removed {} from {}".format(key, guild_id))

        del self.__data[str(guild_id)][key]        
        self._save()
        self.__need_update.append(guild_id)
        
        return data

    async def loop_thro(self) -> dict:
        """
        Loop through all the Assignments in the system
        to find the passed one and return it.
        """
        log.debug('looping througth all assignment...')
        changes = dict()
        for guild_id in self.__data:
            for key in self.__data[guild_id]:
                already_passed = self.check_passed_date(self.__data[guild_id][key]["date"])

                if already_passed != self.__data[guild_id][key]['already-passed']:
                    if guild_id not in changes: 
                        changes[guild_id] = {}

                    self.__data[guild_id][key]['already-passed'] = already_passed
                    changes[guild_id][key] = self.__data[guild_id][key]
        
        self._save()
        self.__need_update.append([int(i) for i in changes])
        return changes
    
    async def delete_old_work(self) -> int:
        """
        Delete the passed works data if It has reached the maximum days which defined in config.py
        Will return amount of deleted work.
        """
        log.debug('checking old work to delete')
        need_to_delete = {}
        count = 0

        # Finding work to delete.
        for guild_id in self.__data:
            for key, data in self.__data[guild_id].items():
                day_passed = self.bot.in_days(  data.get( "date-tracker", data.get("date") )  )

                if day_passed is None or day_passed >= 0: 
                    # Unable to identify date or Alrady passed
                    continue 

                if abs(day_passed) >= self.bot.config.maximum_days: # If It's already passed and more than maximum days.
                    count += 1

                    if guild_id not in need_to_delete:
                        need_to_delete[guild_id] = [key]
                        continue
                    
                    need_to_delete[guild_id].append(key)

        # Actually Delete the work to avoid RunTimeError
        for guild_id in need_to_delete:
            for key in need_to_delete[guild_id]:
                await self.remove(guild_id, key)

        log.debug(f'found {count}')
        return count

    def _save(self) -> None:
        """
        SAVE!, WHAT DO YOU THINK IT WILL DO?
        """
        self.bot.database.dumps("WORKS", self.__data)

    def delete_guild(self, guild_id: int) -> bool:
        """
        Delete All Guild data including Guild ID from the database.
        """
        if str(guild_id) in self.__data:
            del self.__data[str(guild_id)]
            self._save()
            
            log.debug(f'deleted {guild_id}')

            return True
        
        log.debug(f'unable to delete {guild_id}')
        return False

    def _create_if_nexist(self, guild_id: int) -> bool:
        """
        Create a Guild Data if not Existed in the database.
        """
        if str(guild_id) not in self.__data:
            self.__data[str(guild_id)] = {}            
            self._save()

            log.info("added new guild {}".format(guild_id))
            return True
        return False

    def check_passed_date(self, date: str) -> bool:
        """
        Check if the given date passed or not.
        """

        try:
            return self.try_strp_date(date) < datetime.datetime.strptime(today_th(), "%Y-%m-%d")    
        except TypeError:
            return False

    def check_valid_guild(self, guild_id: int) -> bool:
        """
        Check if that Guild ID is valid (in the database).
        """
        return str(guild_id) in self.__data

    def generate_key(self, char_limit: int = 8) -> str:
        """
        Generate a key base on char limit.
        Normally set to 8
        """
        log.debug('generated new key')
        return secrets.token_hex(nbytes=char_limit)[:char_limit]

    def strp_able(self, unreadable: str) -> bool:
        """
        Check if the Date that were given stripable or not.
        """
        try:
            datetime.datetime.strptime(unreadable, "%A %d %B %Y")
        except ValueError:
            return False
        return True

    def try_strp_date(self, unreadable: str) -> Optional[datetime.datetime]:
        """
        Try to Strip given Date, If can't return the given.
        """        
        if len(unreadable) < 3: 
            return None

        p = unreadable[2]
        try: 
            return datetime.datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
        except ValueError:            
            p = unreadable[1]
            try: 
                return datetime.datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
            except ValueError: 
                return None

    def get_readable_date(self, unreadable: str) -> str:
        """
        Get a normal-human format date.
        """
        strp = self.try_strp_date(unreadable)
        return unreadable if strp is None else strp.strftime("%A %d %B %Y")