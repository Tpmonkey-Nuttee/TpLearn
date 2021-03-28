# Discord bot TpLearn BETA
# @ KUS Senior Project
# Made by Tpmonkey

# Extra Credit to Python Discord & IdleRPG
# For an example on How to make Discord Bot
# https://github.com/python-discord/bot

import os
import logging

from utils.log import setup
from bot import Bot

# Create a webserver.
from webserver import keep_alive
keep_alive()

# Setting up Logging.
setup()
log = logging.getLogger("main")
log.info("Starting program...")

# Create and Run the Bot.
bot = Bot.create()
bot.load_extensions()

token = os.getenv("TOKEN")
bot.run(token)