#!/usr/bin/env bash
cw.sh
cd /data/sfsf/workspace/trunk/
./gradlew --stop
./gradlew clean
./gradlew redeploy --stacktrace
