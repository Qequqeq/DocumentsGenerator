#!/bin/bash

cd "$(dirname "$0")"

echo "==============================="
echo "Starting server...."
echo "==============================="

if [ ! -d ".venv" ]; then
    echo "now installing venv..."
    python3 -m venv .venv
fi

echo "activation virtual enviroment"
source .venv/bin/activate

echo "installing requirements"
pip3 install -r requirements.txt

echo "server started"
uvicorn api_entry:app
