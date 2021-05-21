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

from constant import today_th

import logging
log = logging.getLogger(__name__)

class Planner:
    def __init__(self, bot):
        self.bot = bot
        self.__data = bot.database.loads("WORKS")
        self.__need_update = []
        self.trigger_update()
    
    @property
    def need_update(self) -> list:
        """ Return Guild IDs that need an update. """
        p = list( dict.fromkeys( [str(i) for i in self.__need_update] ) )
        self.__need_update = [str(i) for i in self.__need_update if str(i) not in p]
        return p
    
    def trigger_update(self) -> None:
        log.debug(f'triggered update')
        self.__need_update = self.get_all_guild()

    def get_number_all(self) -> int:
        """
        Get count of all available works.
        """
        c = 0
        for i in self.__data:
            c += len(self.get_all(i))
        return c

    def get_all(self, guild_id: int) -> dict:
        """
        Get all the assignments that exist and still valid from targeted Guild ID.
        """
        if self.create_guild_data_if_not_exist(guild_id):
            return {}
        
        d = []
        for i in self.__data[str(guild_id)]:
            if self.__data[str(guild_id)][i]['already-passed']:
                continue
            value = self.__data[str(guild_id)][i]
            value['key'] = i
            d.append(value)

        return d

    def get(self, guild_id: int, key: str) -> dict:
        """
        Get an Assignment base on key from targeted Guild ID.
        """
        if self.create_guild_data_if_not_exist(guild_id):
            return {}
        
        d = self.__data[str(guild_id)][key]
        d['key'] = key

        return d

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
            for l in data:
                if l['readable-date'] == i and l['key'] not in keys:
                    final.append(l)
        
        # Unknown date should be in front of the Known date.
        log.debug(f'returning sorted date for {guild_id}')
        return unknown_date + final
    
    def get_embed(self, guild_id: int) -> discord.Embed:
        """
        Embed contained a List of all works in that targeted guild.
        """
        if len(self.get_all(guild_id)) == 0:
            log.debug(f'getting embed return nothing for {guild_id}')
            return discord.Embed(
                description = "Looks like You don't have any assignment! \nCongratuation! :heart:",
                colour = discord.Colour.blue(),
                timestamp = datetime.datetime.utcnow()
            ).set_footer(text = "Use add command to add one!")
        
        sorted = self.get_sorted(guild_id)
        formatted = {}
        index = 0

        while index < len(sorted): # Sorted data first, So It can be easily use later!
            dic = sorted[index]
            date_key = self.try_strp_date(dic['date']).strftime("%d-%m-%Y") if self.strp_able(dic['readable-date']) else "unknown"

            if date_key not in formatted: formatted[date_key] = [dic['key']]
            else: formatted[date_key].append(dic['key'])
            
            index += 1
        
        # Let's create base Embed.
        embed = discord.Embed()
        embed.title = "Upcoming Assignment" if len(sorted) == 1 else "Upcoming Assignments"
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text = "Take a look at #active-works channel for more info!")
        embed.description = random.choice( self.bot.config.facts )

        closest_day = None

        for date in formatted:   
            # Create Field Name
            if date == "unknown": name = "Unknown Date"
            else: name = self.bot.get_title(self.get_readable_date(date), date)

            # Create Field Value
            value = ""
            for key in formatted[date]: value += f"`{key}` • { self.get(guild_id, key)['title'] }\n"
            if len(value) >= 1024: value = value[:1020] + "..." # Embed Field Value cannot be longer than 1024 letters

            # Add Field
            embed.add_field(name=name, value=value, inline = False)

            # Track the closest day and use for Embed Colour
            in_days = self.bot.in_days(date)
            if in_days is None: continue            
            elif closest_day is None: closest_day = in_days
            elif in_days < closest_day: closest_day = in_days
        
        embed.colour = self.bot.get_colour(gap=closest_day)
        log.debug(f'return embed for {guild_id}')
        return embed

    def check_valid_key(self, guild_id: int, key: str) -> bool:
        """
        Check if a Assignment key valid on targeted Guild ID or not.
        """
        return key in self.__data[str(guild_id)]

    async def add(self, guild_id: int, **kwargs) -> str:
        """
        Add an Assignment to the targeted Guild ID.
        Need to provide all Assignment Attribute.
        """

        self.create_guild_data_if_not_exist(guild_id)
        title = kwargs.get("title") or "Untitled"
        description = kwargs.get("description") or  "No Description"
        date = kwargs.get("date") or "Unknown"
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
            "date-tracker": date_tracker
        }

        log.debug("added Assignment from `{}` with key `{}`".format(guild_id, key))
        self.save() # don't forget to save!
        self.__need_update.append(guild_id)
        
        return key

    async def remove(self, guild_id: int, key: str) -> Optional[dict]:
        """
        Remove an Assignment base on key from targeted Guild ID.
        """
        if self.create_guild_data_if_not_exist(guild_id):
            return 
        data = self.__data[str(guild_id)][key]
        data["key"] = key 

        log.trace("removed {} from {}".format(key, guild_id))

        del self.__data[str(guild_id)][key]        
        self.save()
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
                date = self.__data[guild_id][key]["date"]
                already_passed = self.check_passed_date(date)

                if already_passed != self.__data[guild_id][key]['already-passed']:
                    if guild_id not in changes: changes[guild_id] = {}

                    self.__data[guild_id][key]['already-passed'] = already_passed
                    changes[guild_id][key] =  self.__data[guild_id][key]
        
        self.save()
        self.__need_update.append([int(i) for i in changes])
        return changes
    
    async def delete_old_work(self) -> int:
        """
        Delete the passed works data if It has reached the maximum days which defined in config.py
        Will return amount of deleted work.
        """
        # We need to define what to delete then delete later to avoid RuntimeError.
        log.debug('checking old work to delete')
        need_to_delete = {}
        count = 0
        for guild_id in self.__data:
            for key, data in self.__data[guild_id].items():
                day_passed = self.bot.in_days(  data.get( "date-tracker", data.get("date") )  )
                if day_passed is None: continue

                if abs(day_passed) >= self.bot.config.maximum_days: # If It's already passed and more than maximum days.
                    count += 1
                    if guild_id not in need_to_delete:
                        need_to_delete[guild_id] = [key]
                        continue
                    need_to_delete[guild_id].append(key)
    
        for guild_id in need_to_delete:
            for key in need_to_delete[guild_id]:
                await self.remove(guild_id, key)

        return count

    def save(self) -> None:
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
            self.save()
            log.debug(f'deleted {guild_id}')
            return True
        log.debug(f'unable to delete {guild_id}')
        return False

    def create_guild_data_if_not_exist(self, guild_id: int) -> bool:
        """
        Create a Guild Data if not Existed in the database.
        """
        if str(guild_id) not in self.__data:
            self.__data[str(guild_id)] = {}
            log.info("added new guild {}".format(guild_id))

            self.save()
            return True
        return False

    def check_passed_date(self, date: str) -> bool:
        """
        Check if the given date passed or not.
        """
        today_ = datetime.datetime.strptime(today_th(), "%Y-%m-%d")    
        thatday = self.try_strp_date(date)

        try:
            return thatday < today_
        except:
            return False

    def check_valid_guild(self, guild_id: int) -> bool:
        """
        Check if that Guild ID is valid (in the database).
        """
        return str(guild_id) in self.__data

    def generate_key(self, char_limit: int = 8) -> None:
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
        except:
            return False
        return True

    def try_strp_date(self, unreadable: str) -> Optional[str]:
        """
        Try to Strip given Date, If can't return the given.
        """
        
        if len(unreadable) < 3: return None
        p = unreadable[2]
        try: strp = datetime.datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
        except:
            p = unreadable[1]
            try: strp = datetime.datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
            except: return None
        return strp

    def get_readable_date(self, unreadable: str) -> str:
        """
        Get a normal-human format date.
        """
        strp = self.try_strp_date(unreadable)
        return unreadable if strp is None else strp.strftime("%A %d %B %Y")