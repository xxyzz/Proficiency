#!/usr/bin/env bash

if [[ "$OSTYPE" != "msys" ]]; then
    python3 -m venv .venv
    source .venv/bin/activate
else
    py -m venv .venv
    source .venv/Scripts/activate
fi

python -m pip install -r requirements.txt

python main.py && deactivate
