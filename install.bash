#! /bin/bash

# Not finished, For moving on to VPS in the future.

sudo apt update
sudo apt upgrade

sudo apt install git
sudo apt install curl

# Install redis
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg

sudo apt-get update
sudo apt-get install redis

# For pyproject.toml file
sudo apt install python3-poetry
sudo apt install python3-cachecontrol

# Creating Bot directory
mkdir TpLearn
cd TpLearn

git clone https://github.com/Tpmonkey-Nuttee/TpLearn.git
poetry install

echo "Please clone `default_config.json` and rename to `config.json` then set up the config file."