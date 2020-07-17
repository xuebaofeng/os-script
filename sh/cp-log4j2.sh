#!/usr/bin/env bash
docker cp bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/log4j2.xml /mnt/hgfs/vm/log4j2-compose.xml
docker cp /mnt/hgfs/vm/log4j2.xml bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/
cp ${GRADLE_WORKSPACE}/tomcat-sfs/sf_conf/log4j2.xml /mnt/hgfs/vm/log4j2-override.xml
cp /mnt/hgfs/vm/log4j2.xml ${GRADLE_WORKSPACE}/tomcat-sfs/sf_conf/
