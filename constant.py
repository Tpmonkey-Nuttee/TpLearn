"""
Bot Constant, contained Database and some datetime.
Made by Tpmonkey
"""

from typing import Any, Optional
from replit import db

import traceback
import datetime
import logging
import pytz

_log = logging.getLogger(__name__)

def today(raw: bool = False) -> datetime.datetime:
    """ Return today date/time. """
    r = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
        pytz.timezone("Etc/GMT-1"))
    return r if raw else str(r)[:10].strip()

def today_th(raw: bool = False) -> datetime.datetime:
    """ Return today date/time. """
    r = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(
        pytz.timezone("Etc/GMT-7"))
    return r if raw else str(r)[:10].strip()

class Database:
    def __init__(self):
        _log.debug("init database succesful")
    
    async def load(self, key: str) -> Any:
        """ Load data safely from database. """
        try: return db[key]
        except:
            _log.warning(traceback.format_exc())
            return None        

    async def dump(self, key: str, value: Any) -> bool:
        """ Dump data safely to database. """
        try: db[key] = value
        except:
            _log.warning(traceback.format_exc())
            return False
        return True
    
    def loads(self, key: str) -> Optional[Any]:
        """ Load data cautiously from database. """
        try: 
            return db[key]
        except:
            _log.warning(traceback.format_exc())        

    def dumps(self, key: str, value: Any) -> bool:
        """ Dump data cautiously to database. """
        try: db[key] = value
        except:
            _log.warning(traceback.format_exc())
            return False
        return True