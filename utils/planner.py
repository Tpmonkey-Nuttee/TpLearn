import secrets
from datetime import datetime
from constant import Database, today
from typing import Optional

import logging

log = logging.getLogger(__name__)

db = Database()
main_data = db.loads("WORKS")

class Payload:
    def __init__(self, display=None, data = None, success = True):
        self.display = display
        self.success = success
        self.data = data
    
    def __repr__(self):
        return self.display

async def get_all(guild_id: int) -> Payload:
    return Payload(display = main_data[str(guild_id)])

async def add(guild_id: int, **kwargs) -> Payload:
    create_guild_data_if_not_exist(guild_id)
    title = kwargs.get("title") or "Untitled"
    description = kwargs.get("description") or "No Description"
    date = kwargs.get("date") or "Unknown"
    image_url = kwargs.get("image_url")

    key = generate_key()

    main_data[str(guild_id)][key] = {
        "title": title,
        "desc": description,
        "date": date,
        "image-url": image_url,
        "readable-date": get_readable_date(date),
        "already-passed": check_passed_date(date),
        "sended": [],
        "finished": []
    }

    log.debug("Added Assignment from `{}` with key `{}`".format(guild_id, key))

    save()
    # print(main_data)

    return Payload(display = key)

async def remove(guild_id: int, key: str) -> Payload:
    if create_guild_data_if_not_exist(guild_id):
        return Payload(success = False, display = False)
    data = main_data[str(guild_id)][key] 
    try:
        del main_data[str(guild_id)][key]
    except Exception as e:
        log.warning("Unable to remove Assignment at {} with key {}\nException: {}".format(guild_id, key, e))
        return Payload(success=False, display = False)
        
    save()
    
    return Payload(display = key, data= data)
    # {"sucess": True, "key": key, "info": data}

async def loop_tho() -> dict:
    changes = dict()
    for guild_id in main_data:
        for key in main_data[guild_id]:
            date = main_data[guild_id][key]["date"]
            already_passed = check_passed_date(date)

            if already_passed != main_data[guild_id][key]['already-passed']:
                if guild_id not in changes:
                    changes[guild_id] = {}

                main_data[guild_id][key]['already-passed'] = already_passed
                changes[guild_id][key] =  main_data[guild_id][key]  
    return changes        

def save() -> None:
    # print(main_data)
    db.dumps("WORKS", main_data)

def create_guild_data_if_not_exist(guild_id: int) -> bool:
    if str(guild_id) not in main_data:
        main_data[str(guild_id)] = {}
        log.info("Added new guild {}".format(guild_id))
        return True
    return False

def check_passed_date(date: str) -> bool:
    today_ = today()
    today_ = datetime.strptime(today_, "%Y-%m-%d")
    
    thatday = try_strp_date(date)

    try:
        return thatday < today_
    except:
        return False

def check_valid_guild(guild_id: int) -> bool:
    return True if str(guild_id) in main_data else False

def generate_key(char_limit: int = 8) -> None:
    key = secrets.token_hex(nbytes=char_limit)
    return key[:char_limit]

def try_strp_date(unreadable: str) -> Optional[str]:
    p = unreadable[2]
    try:
        strp = datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
    except:
        p = unreadable[1]
        try:
            strp = datetime.strptime(unreadable, f"%d{p}%m{p}%Y")
        except:
            return None
    return strp

def get_readable_date(unreadable: str) -> str:
    
    strp = try_strp_date(unreadable)

    if strp is None:
        return unreadable

    return strp.strftime("%A %d %B %Y")