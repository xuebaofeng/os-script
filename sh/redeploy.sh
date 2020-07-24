#!/usr/bin/env bash
cw.sh
cd ${GRADLE_WORKSPACE}/
./gradlew deploy
#./gradlew redeploy --rerun-tasks --no-build-cache
