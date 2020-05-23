#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/
./gradlew upgradeTomcat --stacktrace  -Dargs="-devMode"
./gradlew migrateTomcat --stacktrace
