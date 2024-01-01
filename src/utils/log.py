"""
Logging Setup
Made by Python Discord Bot team on Github.
Credit: https://github.com/python-discord/bot
"""

import logging
import datetime
from pathlib import Path
from logging import Logger, handlers

__all__ = ("setup", )

TRACE_LEVEL = 5

DATE = str(datetime.date.today())[:-3]

class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record):
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False
        return True


def setup() -> None:
    """ Set up loggers. """
    logging.TRACE = TRACE_LEVEL
    logging.addLevelName(TRACE_LEVEL, "TRACE")
    Logger.trace = _monkeypatch_trace

    format_string = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    log_format = logging.Formatter(format_string)

    log_file = Path("logs", f"bot-{DATE}.log")
    log_file.parent.mkdir(exist_ok=True)
    file_handler = handlers.RotatingFileHandler(log_file, maxBytes=5242880, backupCount=7, encoding="utf8")
    file_handler.setFormatter(log_format)

    logging.getLogger('discord').setLevel(logging.DEBUG)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.state').addFilter(RemoveNoise())

    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.getLogger("spotipy.client").setLevel(logging.WARNING)
    logging.getLogger("spotipy.oauth2").setLevel(logging.WARNING)    

    logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)    

    root_log = logging.getLogger()
    root_log.setLevel(logging.NOTSET)
    root_log.addHandler(file_handler)


def _monkeypatch_trace(self: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log 'msg % args' with severity 'TRACE'.

    To pass exception information, use the keyword argument exc_info with
    a true value, e.g.

    logger.trace("Houston, we have an %s", "interesting problem", exc_info=1)
    """
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, msg, args, **kwargs)