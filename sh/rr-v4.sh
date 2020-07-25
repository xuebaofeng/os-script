#!/usr/bin/env bash
set -e
start-services.sh
redeploy.sh
start-tomcat-sfs.sh
