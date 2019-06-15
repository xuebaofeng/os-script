#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/
./gradlew upgradeTomcat --stacktrace  -Dargs="-devMode"
./gradlew migrateTomcat --stacktrace
