#! /bin/bash

# Not finished, For moving on to VPS in the future.

sudo apt update
sudo apt upgrade

# Install redis
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg

sudo apt-get update
sudo apt-get install redis

# For pyproject.toml file
sudo apt install python3-poetry
sudo apt install python3-cachecontrol

# Install poetry
poetry install