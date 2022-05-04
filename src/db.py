import redis
import pickle
import traceback
from logging import getLogger
from typing import Any, Optional

log = getLogger(__name__)

class RedisDatabase:
    def __init__(self):
        self.pool = redis.Redis()

        assert self.ping(), "Cannot connect to Redis server."
    
    def ping(self) -> bool:
        try:
            self.pool.ping()
        except (redis.exceptions.ConnectionError, ConnectionRefusedError):
            return False
        return True
    
    def loads(self, key: str, backoff: Any = None) -> Any:
        """Get value at a key. If doesn't exist, return backoff.

        Args:
            key (str): Redis Key.
            backoff (Any, optional): Backoff value to return. Defaults to None.

        Returns:
            Any: Value at a key.
        """
        ret = self.pool.get(key)

        if ret is None:
            return backoff
        return pickle.loads(ret)
    
    async def load(self, key :str, backoff: Any = None) -> Any:
        """(Async) Get value at a key. If doesn't exist, return backoff.

        Args:
            key (str): Redis key.
            backoff (Any, optional): Backoff value to return. Defaults to None.

        Returns:
            Any: Value at a key.
        """
        ret = self.pool.get(key)

        if ret is None:
            return backoff
        return pickle.loads(ret)
    
    def dumps(self, key: str, value: Any, **kwargs) -> bool:
        """Set value at a key.

        Args:
            key (str): Redis key.
            value (Any): Value to set (Will be turn into bytes)
            kwargs (kwargs): https://redis-py.readthedocs.io/en/stable/commands.html#redis.commands.core.CoreCommands.set

        Returns:
            bool: Success or not.
        """
        try:
            self.pool.set(
                name = key,
                value = pickle.dumps(value),
                **kwargs
            )
        except Exception as e: # A lot to expect.
            log.warning(f"Cannot set key {key}; {e}")
            return False
        return True

    async def dump(self, key: str, value: Any, **kwargs) -> bool:
        """(Async) Set value at a key.

        Args:
            key (str): Redis key.
            value (Any): Value to set (Will be turn into bytes)
            kwargs (kwargs): https://redis-py.readthedocs.io/en/stable/commands.html#redis.commands.core.CoreCommands.set

        Returns:
            bool: Success or not.
        """
        try:
            self.pool.set(
                name = key,
                value = pickle.dumps(value),
                **kwargs
            )
        except Exception as e: # A lot to expect.
            log.warning(f"Cannot set key {key}; {e}")
            return False
        return True


class ReplitDatabase:
    def __init__(self):
        log.debug("init database succesful")
    
    async def load(self, key: str, go_back: Any = None) -> Any:
        """ Load data safely from database. """
        try: 
            return replit.db[key]
        except KeyError:
            log.warning(traceback.format_exc())
            return go_back

    async def dump(self, key: str, value: Any) -> bool:
        """ Dump data safely to database. """
        try: 
            replit.db[key] = value
        except Exception: # I don't even know what are we trying to catch.
            log.warning(traceback.format_exc())
            return False
        return True
    
    def loads(self, key: str, go_back: Any = None) -> Optional[Any]:
        """ Load data cautiously from database. """
        try: 
            return replit.db[key]
        except KeyError:
            log.warning(traceback.format_exc())        
            return go_back

    def dumps(self, key: str, value: Any) -> bool:
        """ Dump data cautiously to database. """
        try: 
            replit.db[key] = value
        except Exception:
            log.warning(traceback.format_exc())
            return False
        return True

try:
    import replit
except (ImportError, ModuleNotFoundError):
    log.info("Database: REDIS")
    Database = RedisDatabase
else:
    log.info("Database: REPLIT")
    Database = ReplitDatabase