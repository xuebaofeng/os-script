#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/bizx-docker-dev
#docker-compose stop kafka
docker-compose stop hana
docker-compose up -d hana
