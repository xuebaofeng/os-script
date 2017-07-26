#!/usr/bin/env bash
docker stop $(docker ps -a -q)
docker container prune -f
start-oracle.sh