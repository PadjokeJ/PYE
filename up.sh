#!/bin/bash

docker compose up postgres -d
uv run src/main.py
