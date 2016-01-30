#!/usr/bin/env bash
python -m SimpleHTTPServer 9999 &
ngrok http 9999