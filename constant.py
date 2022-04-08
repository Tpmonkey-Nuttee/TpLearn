"""
Bot Constant, contained Database and some datetime.
Made by Tpmonkey
"""

from typing import Any, Optional
try:
    from replit import db
except ImportError:
    raise ImportError("This bot uses replit database system. Please run it on replit.com")

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
    # TODO: Fix this mess please.
    def __init__(self):
        _log.debug("init database succesful")
    
    async def load(self, key: str, go_back: Any = None) -> Any:
        """ Load data safely from database. """
        try: 
            return db[key]
        except KeyError:
            _log.warning(traceback.format_exc())
            return go_back

    async def dump(self, key: str, value: Any) -> bool:
        """ Dump data safely to database. """
        try: 
            db[key] = value
        except Exception: # I don't even know what are we trying to catch.
            _log.warning(traceback.format_exc())
            return False
        return True
    
    def loads(self, key: str, go_back: Any = None) -> Optional[Any]:
        """ Load data cautiously from database. """
        try: 
            return db[key]
        except KeyError:
            _log.warning(traceback.format_exc())        
            return go_back

    def dumps(self, key: str, value: Any) -> bool:
        """ Dump data cautiously to database. """
        try: 
            db[key] = value
        except Exception:
            _log.warning(traceback.format_exc())
            return False
        return True