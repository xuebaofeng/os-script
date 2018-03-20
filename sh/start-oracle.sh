#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/bizx-docker-dev
docker-compose pull oracle
docker-compose up -d oracle
