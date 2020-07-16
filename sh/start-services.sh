#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/bizx-docker-dev
docker-compose up -d zookeeper kafka hana
