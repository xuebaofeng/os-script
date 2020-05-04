#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/bizx-docker-dev
export DBTYPE=hana2
docker-compose up -d hana2
