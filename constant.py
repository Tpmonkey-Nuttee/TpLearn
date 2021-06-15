"""
Bot Constant, contained Database and some datetime.
Made by Tpmonkey
"""

from typing import Any, Optional, List, Union, Callable, Iterator, Dict
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
        """ Load data cautiously to database. """
        try: return db[key]
        except:
            _log.warning(traceback.format_exc())        

    def dumps(self, key: str, value: Any) -> bool:
        """ Dump data cautiously to database. """
        try: db[key] = value
        except:
            _log.warning(traceback.format_exc())
            return False
        return True


from collections import abc
import asyncio
import urllib
import json
import os

_db_url = os.getenv('REPLIT_DB_URL')

class ObservedList(abc.MutableSequence):
    __slots__ = ("_on_mutate_handler", "value")

    def __init__(
        self, on_mutate: Callable[[List], None], value: Optional[List] = None
    ) -> None:
        self._on_mutate_handler = on_mutate
        if value is None:
            self.value = []
        else:
            self.value = value

    def on_mutate(self) -> None:
        """Calls the mutation handler with the underlying list as an argument."""
        self._on_mutate_handler(self.value)

    def __getitem__(self, i: Union[int, slice]) -> Any:
        return self.value[i]

    def __setitem__(self, i: Union[int, slice], val: Any) -> None:
        self.value[i] = val
        self.on_mutate()

    def __delitem__(self, i: Union[int, slice]) -> None:
        del self.value[i]
        self.on_mutate()

    def __len__(self) -> int:
        return len(self.value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.value)

    def __imul__(self, rhs: Any) -> Any:
        self.value *= rhs
        self.on_mutate()
        return self.value

    def __eq__(self, rhs: Any) -> bool:
        return self.value == rhs

    def insert(self, i: int, elem: Any) -> None:
        """Inserts a value into the underlying list."""
        self.value.insert(i, elem)
        self.on_mutate()

    def set_value(self, value: List) -> None:
        """Sets the value attribute and triggers the mutation function."""
        self.value = value
        self.on_mutate()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(value={self.value!r})"

class ObservedDict(abc.MutableMapping):
    __slots__ = ("_on_mutate_handler", "value")

    def __init__(
        self, on_mutate: Callable[[Dict], None], value: Optional[Dict] = None
    ) -> None:
        self._on_mutate_handler = on_mutate
        if value is None:
            self.value = {}
        else:
            self.value = value

    def on_mutate(self) -> None:
        """Calls the mutation handler with the underlying dict as an argument."""
        self._on_mutate_handler(self.value)

    def __contains__(self, k: Any) -> bool:
        return k in self.value

    def __getitem__(self, k: Any) -> Any:
        return self.value[k]

    def __setitem__(self, k: Any, v: Any) -> None:
        self.value[k] = v
        self.on_mutate()

    def __delitem__(self, k: Any) -> None:
        del self.value[k]
        self.on_mutate()

    def __iter__(self) -> Iterator[Any]:
        return iter(self.value)

    def __len__(self) -> int:
        return len(self.value)

    def __eq__(self, rhs: Any) -> bool:
        return self.value == rhs

    def __imul__(self, rhs: Any) -> Any:
        self.value *= rhs
        self.on_mutate()
        return self.value

    def set_value(self, value: Dict) -> None:
        """Sets the value attribute and triggers the mutation function."""
        self.value = value
        self.on_mutate()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(value={self.value!r})"


def to_primitive(o: Any) -> Any:
    if isinstance(o, ObservedList) or isinstance(o, ObservedDict):
        return o.value
    return o

class DBJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        return to_primitive(o)

def _dumps(val: Any) -> str:
    return json.dumps(val, separators=(",", ":"), cls=DBJSONEncoder)

class AsyncDatabase:
    __slots__ = ("__bot", "__session", "__url")

    def __init__(self, bot):
        self.__bot = bot
        self.__session = bot.trust_session
        self.__url = _db_url
    
    async def load(self, key: str) -> Any:
        async with self.__session.get(
            self.__url+ "/" + urllib.parse.quote(key), raise_for_status = True
        ) as r:
            if r.status == 404:
                raise KeyError(key)
            return json.loads( await r.text() )
    
    async def dump(self, key: str, value: Any) -> None:
        await self.dump_raw(key, _dumps(value))

    async def dump_raw(self, key: str, value: str) -> None:
        await self.request_post({key: value})
    
    async def request_post(self, value: Dict) -> None:
        await self.__session.post(
            self.__url, data=value, raise_for_status = True
        )
    
    async def delete(self, key: str) -> None:
        await self.__session.delete(
            self.__url+ "/" + urllib.parse.quote(key), raise_for_status = True
        )
    
    def loads(self, key: str) -> Any:
        return asyncio.get_event_loop().run_until_complete(self.load(key))
    
    def dumps(self, key: str, value: Any) -> None:
        asyncio.get_event_loop().run_until_complete(self.dump(key, value))