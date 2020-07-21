#!/usr/bin/env bash
newgrp docker
log4j2_location=/shared
docker cp bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/log4j2.xml ${log4j2_location}/log4j2-compose.xml
docker cp ${log4j2_location}/log4j2.xml bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/
cp ${GRADLE_WORKSPACE}/tomcat-sfs/sf_conf/log4j2.xml ${log4j2_location}/log4j2-override.xml
cp ${log4j2_location}/log4j2.xml ${GRADLE_WORKSPACE}/tomcat-sfs/sf_conf/
