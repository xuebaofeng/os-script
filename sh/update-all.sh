#!/usr/bin/env bash
docker stop $(docker ps -a -q)
docker container prune -f
update-code.sh