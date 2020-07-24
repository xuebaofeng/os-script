#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/
cw.sh
./gradlew tomcatGenerateSfs --stacktrace
