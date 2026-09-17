#!/bin/bash

docker compose up postgress -d
uv run src/main.py
