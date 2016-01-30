#!/usr/bin/env bash
lsof -P | grep ':9999' | awk '{print $2}' | xargs kill -9
python -m SimpleHTTPServer 9999 &
ngrok http 9999