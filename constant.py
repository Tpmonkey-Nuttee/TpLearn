# Bot Backend
# Made by Tpmonkey
# Credit: Repl.it database

import pytz
import logging
import datetime
import traceback
from typing import Any, Optional

from replit import db

log = logging.getLogger(__name__)

def today(raw=False) -> datetime.datetime:
    # Return today date/time
    r = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
        pytz.timezone("Etc/GMT-1"))
    if not raw:
        r = str(r)[:10].strip()
    return r

def today_th(raw=False) -> datetime.datetime:
    # Return today date/time
    r = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
        pytz.timezone("Etc/GMT-7"))
    if not raw:
        r = str(r)[:10].strip()
    return r

class Database:
    async def load(self, key: str) -> Any:
        # Load data from database
        try:
            r = db[key]
        except:
            traceback.print_exc()
            log.warning(traceback.format_exc())
            return None
        return r

    async def dump(self, key: str, value: Any) -> bool:
        # Dump data to database
        try:
            db[key] = value
        except:
            traceback.print_exc()
            log.warning(traceback.format_exc())
            return False
        return True
    
    def loads(self, key: str) -> Optional[Any]:
        try:
            ret = db[key]
        except:
            traceback.print_exc()
            log.warning(traceback.format_exc())
        return ret

    def dumps(self, key: str, value: Any) -> bool:
        try:
            db[key] = value
        except:
            traceback.print_exc()
            log.warning(traceback.format_exc())
            return False
        return True