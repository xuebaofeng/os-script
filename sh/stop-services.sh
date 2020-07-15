#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/bizx-docker-dev
docker-compose stop zookeeper kafka hana
