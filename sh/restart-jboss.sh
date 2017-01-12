#!/usr/bin/env bash
export JBOSS_HOME=/data/sfsf/workspace/trunk/jboss-sfs
cd /data/sfsf/workspace/trunk
gradle updateJbossSfs
restart-docker.sh
cd /data/sfsf/workspace/trunk/jboss-sfs/bin
./runMain.sh DEBUG
