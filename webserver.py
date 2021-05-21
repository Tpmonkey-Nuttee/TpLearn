"""
Bot Webserver to keep the bot alive.
Made by ??? (can be found across replit.com)
"""

from threading import Thread
from flask import Flask
import logging

app = Flask('')

# Disable built-in Logger
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True

@app.route('/')
def main():
    return "The bot is online!"
def run():
    app.run(host="0.0.0.0", port=8080)
def keep_alive():
    Thread(target=run).start()