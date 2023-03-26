"""
Discord bot TpLearn [BETA]
@KUS Senior Project
Made by Tpmonkey (Nuttee) KUS48

* Extra Credit to Python Discord & IdleRPG, for providing example of discord bot.
"""

import os
os.system("python3 -m poetry install")

# Setting up Logging.
from utils.log import setup
setup()

# Setting up webserver
from webserver import keep_alive
log = keep_alive()

# Create and Run the Bot.
from bot import Bot

import discord
discord.utils.setup_logging()

bot = Bot.create()   

# await bot.load_extensions()
token = os.getenv("TOKEN")
bot.run(token)