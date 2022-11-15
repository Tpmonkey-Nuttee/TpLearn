"""
Discord bot TpLearn [BETA]
@KUS Senior Project
Made by Tpmonkey (Nuttee) KUS48

* Extra Credit to Python Discord & IdleRPG, for providing example of discord bot.
"""

import os
# Ensure packages are installed, work around for replit :/
os.system("python3 -m poetry install")


# Setting up Logging.
from discord.utils import setup_logging
from utils.log import setup

setup_logging()
setup()


# Setting up webserver
from webserver import keep_alive
keep_alive()


# Create and Run the Bot.
from bot import Bot

if __name__ == "__main__":
    bot = Bot.create()   
    token = os.getenv("TOKEN")
    bot.run(token)