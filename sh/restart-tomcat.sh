#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk
cp build-system/sfs-local-overrides/tomcat-dev-docker-oracle/build.properties build-system/
gradle updateTomcatSfs
cd /data/sfsf/workspace/trunk/bizx-docker-dev
restart-docker.sh
$CATALINA_HOME/bin/startSFS.sh
