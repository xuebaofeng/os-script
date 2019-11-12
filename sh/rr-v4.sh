#!/usr/bin/env bash
start-hana.sh
. java8.sh
redeploy.sh
start-v4.sh "$@"
