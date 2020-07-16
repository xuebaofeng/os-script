#!/usr/bin/env bash
start-services.sh
cd ${GRADLE_WORKSPACE}/bizx-docker-dev
docker cp bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/log4j2.xml /mnt/hgfs/vm/log4j2.xml.bak
docker cp /mnt/hgfs/vm/log4j2.xml bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/
export TOMCAT_MEM=8G
docker-compose up tomcat-dev
