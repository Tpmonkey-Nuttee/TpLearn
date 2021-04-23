# Bot Backend
# Made by Tpmonkey
# Credit: Repl.it database

from typing import Any, Optional
from replit import db
import traceback
import datetime
import logging
import pytz

log = logging.getLogger(__name__)

def today(raw=False) -> datetime.datetime:
    # Return today date/time
    r = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
        pytz.timezone("Etc/GMT-1"))
    return r if raw else str(r)[:10].strip()

def today_th(raw=False) -> datetime.datetime:
    # Return today date/time
    r = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
        pytz.timezone("Etc/GMT-7"))
    return r if raw else str(r)[:10].strip()

class Database:
    async def load(self, key: str) -> Any:
        # Load data from database
        try:
            r = db[key]
        except:
            log.warning(traceback.format_exc())
            return None
        return r

    async def dump(self, key: str, value: Any) -> bool:
        # Dump data to database
        try:
            db[key] = value
        except:
            log.warning(traceback.format_exc())
            return False
        return True
    
    def loads(self, key: str) -> Optional[Any]:
        try:
            ret = db[key]
        except:
            log.warning(traceback.format_exc())
        return ret

    def dumps(self, key: str, value: Any) -> bool:
        try:
            db[key] = value
        except:
            log.warning(traceback.format_exc())
            return False
        return True