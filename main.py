"""
Discord bot TpLearn [BETA]
@KUS Senior Project
Made by Tpmonkey (Nuttee) KUS48

* Extra Credit to Python Discord & IdleRPG, for providing example of discord bot.
"""

import os

from utils.log import setup
from bot import Bot

# Create a webserver.
# from webserver import keep_alive
# keep_alive()

# Setting up Logging.
setup()
# Create and Run the Bot.
bot = Bot.create()
bot.load_extensions()

token = os.getenv("TOKEN")
bot.run(token)