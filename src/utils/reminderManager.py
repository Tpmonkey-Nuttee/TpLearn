# TODO: frontend commands.
# TODO: Hook it to exts.dayloop

from utils.time import today_th
from config import MAX_REMINDER_PER_DAY

from enum import Enum

DB_KEY = "REMINDERS"

class Day(Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DAYS_ENUM = (Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY, Day.THURSDAY, Day.FRIDAY, Day.SATURDAY, Day.SUNDAY)
DEFAULT_PROFILE = {i: [] for i in DAYS}

class TooManyReminders(Exception):
    "An exception raise when user exceed reminders limit."
    pass


class ReminderManager:
    """
    Reminder Manager Class.

    Attributes
    -----------
    data: <class 'dict'>
        contain all user data.

    Data Stucture
    -----------  
    {
        "uid1": {
            "Monday": ["1st reminder", "2nd reminder"],
            "Tuesday": ["1st reminder", "2nd reminder"],
            ...
        },
        "uid2": {
            ...
        }
    }

    """
    def __init__(self, bot):
        self.bot = bot
        self.__data = bot.database.loads(DB_KEY, {})

    @property
    def data(self) -> dict:
        """Return all data."""
        return self.__data
    
    def save(self) -> None:
        """Save Data."""
        self.bot.database.dumps(DB_KEY, self.__data)

    def init_profile(self, uid: int) -> None:
        """
        Init User Profile. (aka data)
        NOTE: This function will not save automatically.

        Parameters
        -----------
        uid: <class 'int'>
            Discord User ID.
        """
        uid = str(uid)
        if uid in self.__data:
            return

        self.__data[uid] = DEFAULT_PROFILE
    
    def del_profile(self, uid: int) -> None:
        """
        Delete User Profile.

        Args:
            uid (int): Discord User ID
        """
        
        try:
            del self.__data[str(uid)]
        except KeyError:
            pass

    def add(self, uid: int, day: Day, text: str) -> dict:
        """
        Add a Reminder.

        Parameters
        -----------
        uid: <class 'int'>
            Discord User ID.
        day: <class 'Day'>
            Day enum.
        text: <class 'str'>
            Message that want to be remind.

        Returns
        -----------
        data: <class 'dict'>
            userID: <class 'int'>
                Discord User ID.
            dayName: <class 'str'>
                Day name in English.
            dayValue: <class 'int'>
                Day index, Monday is 0
            text: <class 'str'>
                Message that want to be remind.
            info: <class 'list'>
                All messages that will be remind in an input day.
            allInfo: <class 'dict'>
                Entire users data containing every days.
        
        Raise
        -----------
        :exc: 'TooManyReminders'
            when reminder is exceeding limit.
        """
        self.init_profle(uid)

        dayName = DAYS[day.value]
        if len(self.__data[str(uid)][dayName]) < MAX_REMINDER_PER_DAY:
            self.__data[str(uid)][dayName].append(text.strip())
        else:
            raise TooManyReminders(f"You have exceed reminders limit. (Limit: {MAX_REMINDER_PER_DAY})")

        self.save()

        return {
            "userID": uid,
            "dayName": dayName,
            "dayValue": day.value,
            "text": text.strip(),
            "info": self.__data[str(uid)][dayName],
            "allInfo": self.__data[str(uid)]
        }
    
    def remove(self, uid: int, day: Day, index: int) -> dict:
        """
        Remove a Reminder.

        Parameters
        -----------
        uid: <class 'int'>
            Discord User ID.
        day: <class 'Day'>
            Day enum.
        index: <class 'int'>
            Index of the reminder.

        Returns
        -----------
        data: <class 'dict'>
            userID: <class 'int'>
                Discord User ID.
            dayName: <class 'str'>
                Day name in English.
            dayValue: <class 'int'>
                Day index, Monday is 0
            index: <class 'int'>
                Index of the removed reminder.
            text: <class 'str'>
                Message that was deleted.
            info: <class 'list'>
                All messages that will be remind in an input day.
            allInfo: <class 'dict'>
                Entire users data containing every days.
        
        Raise
        -----------
        :exc: 'IndexError'
            When the given index is invalid.
        """
        self.init_profle(uid)

        dayName = DAYS[day.value]
        try:
            text = self.__data[str(uid)][dayName].pop(index)
        except IndexError:
            raise IndexError("Invalid Index.")
        
        self.save()
        return {
            "userID": uid,
            "dayName": dayName,
            "dayValue": day.value,
            "index": index,
            "text": text.strip(),
            "info": self.__data[str(uid)][dayName],
            "allInfo": self.__data[str(uid)]
        }
    
    def getAll(self, uid: int) -> dict:
        """
        Get all data of a User.

        Parameters
        -----------
        uid: <class 'int'>
            Discord User ID.

        Returns
        -----------
        data: <class 'dict'>
            A data like structure containing all data for that User.
        """
        
        return self.__data.get(str(uid), DEFAULT_PROFILE)
    
    def getToday(self) -> dict:
        """
        Get all reminders that need to be send today.

        Returns
        -----------
        payload: <class 'dict'>
            todayIndex: <class 'int'>
                Today index where Monday is 0.
            todayName: <class 'str'>
                Today name in English.
            users: <class 'dict'>
                key: <class 'str'>
                    Discord User ID.
                value: <class 'list'>
                    List containing all reminder message.

        """
        todayIndex = today_th(True).weekday
        todayName = DAYS[todayIndex]

        payload = {
            "todayIndex": todayIndex,
            "todayName": todayName,
            "users": {}
        }
        for uid in self.__data:
            # If There is a reminder.
            if len(self.__data[uid][todayName]) > 0:
                payload["users"][uid] = self.__data[uid][todayName]
        
        return payload        