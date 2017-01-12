#!/usr/bin/env bash

APPLICATION_SERVER=$1

if [ $# -eq 0 ]
    then
        APPLICATION_SERVER="tomcat"
fi

cp /data/sfsf/workspace/trunk/build-system/sfs-local-overrides/${APPLICATION_SERVER}-dev-docker-oracle/build.properties /data/sfsf/workspace/trunk/build-system/

restart-docker.sh
rebuild-${APPLICATION_SERVER}.sh
rr-${APPLICATION_SERVER}.sh