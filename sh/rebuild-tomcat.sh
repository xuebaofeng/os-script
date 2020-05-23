#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/
./gradlew tomcatCleanSfs --stacktrace
./gradlew tomcatGenerateSfs --stacktrace
