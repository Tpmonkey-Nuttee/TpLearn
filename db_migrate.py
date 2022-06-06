# Database Migrating tools
# Use to transfer data from
# Replit -> Redis

### Settings

URL = "REPLIT DB URL"
TEST = True

### --- 

import json
from typing import Any
from replit.database import database

replit_db = database.Database(URL)

if TEST:
    class TestDatabase:
        def __init__(self) -> None:
            self.data = {}

        def dumps(self, key: str, value: Any) -> None:
            self.data[key] = value

        def show(self) -> None:
            print(json.dumps(self.data, indent=2))

    redis_db = TestDatabase()
else:
    from src.db import RedisDatabase
    redis_db = RedisDatabase()

### --- Assignment: Active and Passed channels
# {
#   "GUILD_ID": {
#       "active": "CHANNEL_ID",
#       "passed": "CHANNEL_ID"
#   }
# }

redis_db.dumps(
    "GUILD", 
    {key: database.to_primitive(value) for key, value in replit_db["GUILD"].items() if value}
)

### --- Music settings
# {
#     "GUILD_ID": {
#         "timeout": int,
#         "annouce_next_song": bool,
#         "vote_skip": bool,
#     }
# }

redis_db.dumps(
    "MUSIC", 
    {key: database.to_primitive(value) for key, value in replit_db["MUSIC"].items()}
)

### --- KUS Monitor: News channels
redis_db.dumps(
    "NEWS-CHANNELS",
    database.to_primitive(replit_db["NEWS-CHANNELS"])
)

### --- KUS Monitor: News IDs
redis_db.dumps(
    "NEWS-IDS",
    database.to_primitive(replit_db["NEWS-IDS"])
)

### --- Day Loop
redis_db.dumps(
    "TODAY", replit_db['TODAY']
)
redis_db.dumps(
    "TODAY-TH", replit_db["TODAY-TH"]
)

### --- Bot version
import src.config
redis_db.dumps(
    "VERSION", src.config.version
)

### --- Assignment: Assignments data
# {
#     "GUILD_ID": {
#         {
#             "key": {
#                 "title": str,
#                 "desc": str,
#                 "date": str,
#                 "image-url": str,
#                 "readable-date": str,
#                 "already-passed": bool,
#                 "date-tracker": str,
#                 "key": str,
#             }
#         }
#     }
# }

data = {}
old = replit_db["WORKS"]

for guild_id in old:
    data[guild_id] = {}
    for key in old[guild_id]:
        data[guild_id][key] = database.to_primitive( old[guild_id][key] )

redis_db.dumps("WORKS", data)

if TEST:
    redis_db.show()