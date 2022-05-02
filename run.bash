#! /bin/bash

# Not finished, For moving on to VPS in the future.

# To keep process alive
screen

# Run Redis server in background
redis-server --daemonize yes

# Run the bot
poetry run python main.py