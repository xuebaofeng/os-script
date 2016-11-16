#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk
gradle updateTomcatSfs
cd /data/sfsf/workspace/trunk/bizx-docker-dev
docker-compose up -d oracle
$CATALINA_HOME/bin/startSFS.sh
