#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/
rm -rf tomcat-sfs/
cw.sh
./gradlew tomcatGenerateSfs --stacktrace
