from bot import Bot

DB_KEY = "REMINDERS"

class ReminderManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.__data = bot.database.loads(DB_KEY, {})
    
    def save(self) -> None:
        self.bot.database.dumps(self.__data)