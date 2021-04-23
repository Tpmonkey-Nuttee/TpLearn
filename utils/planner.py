# A Assignment Manager
# Made by Tpmonkey

from typing import Optional
import datetime
import secrets

from constant import today_th

import logging
log = logging.getLogger(__name__)

class Planner:
    def __init__(self, bot):
        self.bot = bot
        self.main_data = bot.database.loads("WORKS")

    def get_number_all(self) -> int:
        """
        Get count of all available works.
        """

        c = 0
        for i in self.main_data:
            c += len(self.get_all(i))
        return c

    def get_all(self, guild_id: int) -> dict:
        """
        Get all the assignments that exist and still valid from targeted Guild ID.
        """
        if self.create_guild_data_if_not_exist(guild_id):
            return {}
        
        d = []
        for i in self.main_data[str(guild_id)]:
            if self.main_data[str(guild_id)][i]['already-passed']:
                continue
            value = self.main_data[str(guild_id)][i]
            value['key'] = i
            d.append(value)

        return d

    def get(self, guild_id: int, key: str) -> dict:
        """
        Get an Assignment base on key from targeted Guild ID.
        """
        if self.create_guild_data_if_not_exist(guild_id):
            return {}
        
        d = self.main_data[str(guild_id)][key]
        d['key'] = key

        return d

    def get_all_guild(self) -> list:
        """
        Get all Guild IDs.
        """
        return [int(key) for key in self.main_data]

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
        return unknown_date + final

    def check_valid_key(self, guild_id: int, key: str) -> bool:
        """
        Check if a Assignment key valid on targeted Guild ID or not.
        """
        return key in self.main_data[str(guild_id)]

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

        self.main_data[str(guild_id)][key] = {
            "title": title,
            "desc": description,
            "date": date,
            "image-url": image_url,
            "readable-date": self.get_readable_date(date),
            "already-passed": self.check_passed_date(date)
        }

        log.debug("Added Assignment from `{}` with key `{}`".format(guild_id, key))
        self.save() # don't forget to save!
        
        return key

    async def remove(self, guild_id: int, key: str) -> Optional[dict]:
        """
        Remove an Assignment base on key from targeted Guild ID.
        """
        if self.create_guild_data_if_not_exist(guild_id):
            return 
        data = self.main_data[str(guild_id)][key]
        data["key"] = key 

        del self.main_data[str(guild_id)][key]        
        self.save()
        
        return data

    async def loop_thro(self) -> dict:
        """
        Loop through all the Assignments in the system
        to find the passed one and return it.
        """
        changes = dict()
        for guild_id in self.main_data:
            for key in self.main_data[guild_id]:
                date = self.main_data[guild_id][key]["date"]
                already_passed = self.check_passed_date(date)

                if already_passed != self.main_data[guild_id][key]['already-passed']:
                    if guild_id not in changes:
                        changes[guild_id] = {}

                    self.main_data[guild_id][key]['already-passed'] = already_passed
                    changes[guild_id][key] =  self.main_data[guild_id][key]
        self.save()
        return changes        

    def save(self) -> None:
        """
        SAVE!, WHAT DO YOU THINK IT WILL DO?
        """
        self.bot.database.dumps("WORKS", self.main_data)

    def delete_guild(self, guild_id: int) -> bool:
        """
        Delete All Guild data including Guild ID from the database.
        """
        if str(guild_id) in self.main_data:
            del self.main_data[str(guild_id)]
            self.save()
            return True
        return False

    def create_guild_data_if_not_exist(self, guild_id: int) -> bool:
        """
        Create a Guild Data if not Existed in the database.
        """
        if str(guild_id) not in self.main_data:
            self.main_data[str(guild_id)] = {}
            log.info("Added new guild {}".format(guild_id))

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
        return str(guild_id) in self.main_data

    def generate_key(self, char_limit: int = 8) -> None:
        """
        Generate a key base on char limit.
        Normally set to 8
        """
        key = secrets.token_hex(nbytes=char_limit)
        return key[:char_limit]

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
        if len(unreadable) < 3:
            return None
        p = unreadable[2]
        try:
            strp = datetime.datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
        except:
            p = unreadable[1]
            try:
                strp = datetime.datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
            except:
                return None
        return strp

    def get_readable_date(self, unreadable: str) -> str:
        """
        Get a normal-human format date.
        """
        strp = self.try_strp_date(unreadable)

        if strp is None:
            return unreadable

        return strp.strftime("%A %d %B %Y")