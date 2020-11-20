#!/bin/sh

IP=$(ip route | grep docker | awk '{print $9}' | head -n 1);
export EXTERNAL_IP=$IP
export SERVER_PORT=8001

export PYTHONUNBUFFERED=1
export PYCHARM_DEBUG=True

source .env

exec docker-compose up --exit-code-from bot --abort-on-container-exit bot