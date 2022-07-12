import pytz
import time
import datetime
from typing import Any

from dateutil.relativedelta import relativedelta

__all__ = ("time_since", "StatsInTime")


class StatsInTime:
    def __init__(self, limit: int = 10_000) -> None:
        self.limit = limit
        self.stats = []
    
    def append(self, item: Any):
        if len(self.stats) > self.limit:
            self.stats.pop()
        
        self.stats.insert(
            0,
            (item, time.time())
        )
    
    def get_in_last(self, second: int) -> None:
        rn = time.time()
        n = 0
        for _, j in self.stats:
            if rn - second < j:
                break
            n += 1
        
        return n
    

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

# Credit to Python Bot from python discord
def _stringify_time_unit(value: int, unit: str):
    if unit == "seconds" and value == 0:
        return "0 seconds"
    if value == 1:
        return f"{value} {unit[:-1]}"
    if value == 0:
        return f"less than a {unit[:-1]}"
    return f"{value} {unit}"
	
def time_since(past_datetime: datetime.datetime, precision: str = "seconds", max_units: int = 6):
    now = datetime.datetime.utcnow()
    delta = abs(relativedelta(now, past_datetime))

    humanized = humanize_delta(delta, precision, max_units)

    return f"{humanized} ago"

def humanize_delta(delta: relativedelta, precision: str = "seconds", max_units: int = 6):
    if max_units <= 0:
        raise ValueError("max_units must be positive")

    units = (
        ("years", delta.years),
        ("months", delta.months),
        ("days", delta.days),
        ("hours", delta.hours),
        ("minutes", delta.minutes),
        ("seconds", delta.seconds),
    )

    time_strings = []
    unit_count = 0
    for unit, value in units:
        if value:
            time_strings.append(_stringify_time_unit(value, unit))
            unit_count += 1

        if unit == precision or unit_count >= max_units:
            break

    if len(time_strings) > 1:
        time_strings[-1] = f"{time_strings[-2]} and {time_strings[-1]}"
        del time_strings[-2]

    if not time_strings:
        humanized = _stringify_time_unit(0, precision)
    else:
        humanized = ", ".join(time_strings)

    return humanized