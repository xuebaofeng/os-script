#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/bizx-docker-dev
cp-log4j2.sh
export TOMCAT_MEM=6G
docker-compose rm -f kafka
docker-compose up -d zookeeper kafka hana
