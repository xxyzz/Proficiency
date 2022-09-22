#!/usr/bin/env bash

set -e

if [[ "$OSTYPE" != "msys" ]]; then
    if [[ ! -d .venv ]]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
else
    if [[ ! -d .venv ]]; then
        py -m venv .venv
    fi
    source .venv/Scripts/activate
fi

python -m pip install -r requirements.txt

python main.py $1

deactivate
