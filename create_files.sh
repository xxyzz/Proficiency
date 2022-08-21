#!/usr/bin/env bash

if [[ "$OSTYPE" != "msys" ]]; then
    python3 -m venv .venv
    source .venv/bin/activate
else
    py -m venv .venv
    source .venv/Scripts/activate
fi

if [[ $(uname -v) == *"Ubuntu"* && -n "$CI" ]]; then
    python -m pip install --no-cache-dir -U pip
fi

python -m pip install -r requirements.txt

python main.py

deactive
