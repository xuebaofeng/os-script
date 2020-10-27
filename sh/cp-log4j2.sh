#!/usr/bin/env bash
#vms.sh
log4j2_location=/mnt/hgfs/vm
if [ -f ${log4j2_location}/log4j2-compose.xml ]; then
    echo "${log4j2_location}/log4j2-compose.xml exist"
else
docker cp bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/log4j2.xml ${log4j2_location}/log4j2-compose.xml
fi
if [ -f ${log4j2_location}/log4j2-override.xml ]; then
    echo "${log4j2_location}/log4j2-override.xml exist"
else
cp -n ${GRADLE_WORKSPACE}/tomcat-sfs/sf_conf/log4j2.xml ${log4j2_location}/log4j2-override.xml
fi
docker cp ${log4j2_location}/log4j2.xml bizx-docker-dev_tomcat-dev_1:/app/tomcat/sf_conf/
\cp -f ${log4j2_location}/log4j2.xml ${GRADLE_WORKSPACE}/tomcat-sfs/sf_conf/
