#!/usr/bin/env bash
export JBOSS_HOME=/data/sfsf/workspace/trunk/jboss-sfs
cd /data/sfsf/workspace/trunk
gradle updateJbossSfs
cd /data/sfsf/workspace/trunk/bizx-docker-dev
docker-compose up -d hornet
cd /data/sfsf/workspace/trunk/jboss-sfs/bin
./runMain.sh DEBUG
