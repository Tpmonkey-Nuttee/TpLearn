#! /bin/bash

# Not finished, For moving on to VPS in the future.

screen

redis-server --daemonize yes

poetry run python main.py