#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk
gradle updateTomcatSfs
cd /data/sfsf/workspace/trunk/bizx-docker-dev
$CATALINA_HOME/bin/startSFS.sh
