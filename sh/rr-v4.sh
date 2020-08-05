#!/usr/bin/env bash
set -e
start-services.sh
deploy.sh
sfs.sh
