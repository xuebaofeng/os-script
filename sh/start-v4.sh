#!/usr/bin/env bash
start-services.sh
#cd ${GRADLE_WORKSPACE}/tomcat-sfs/bin
#./startSFS.sh
cd ${GRADLE_WORKSPACE}/bizx-docker-dev
docker-compose up tomcat-dev
