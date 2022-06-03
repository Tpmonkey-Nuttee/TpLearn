"""
Discord bot TpLearn [BETA]
@KUS Senior Project
Made by Tpmonkey (Nuttee) KUS48

* Extra Credit to Python Discord & IdleRPG, for providing example of discord bot.
"""

import os

# Setting up Logging.
from utils.log import setup
setup()

from bot import Bot

# Create and Run the Bot.
bot = Bot.create()
bot.load_extensions()

token = os.getenv("TOKEN")
bot.run(token)