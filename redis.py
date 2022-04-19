import redis
import pickle
from typing import Any
from logging import getLogger

from discord.ext import commands

log = getLogger(__name__)

# TODO: new config file

class RedisDatabase:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pool = redis.Redis(
            host = "localhost", 
            port = 6379, # TODO: replace with new config file
            db = 0
        )
    
    def get(self, key: str, backoff: Any = None) -> Any:
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
    
    async def gets(self, key :str, backoff: Any = None) -> Any:
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
    
    def set(self, key: str, value: Any, **kwargs) -> bool:
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

    async def sets(self, key: str, value: Any, **kwargs) -> bool:
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