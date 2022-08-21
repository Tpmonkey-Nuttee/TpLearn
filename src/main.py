"""
Discord bot TpLearn [BETA]
@KUS Senior Project
Made by Tpmonkey (Nuttee) KUS48

* Extra Credit to Python Discord & IdleRPG, for providing example of discord bot.
"""

import os
import asyncio

# Setting up Logging.
from utils.log import setup
setup()

# Setting up webserver
from webserver import keep_alive
keep_alive()

# Create and Run the Bot.
from bot import Bot


async def main():

    bot = Bot.create()
    
    async with bot:
        bot.load_extensions()
        token = os.getenv("TOKEN")
        await bot.start(token)

asyncio.run(main())