#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}/
find ./au-V4/au-V4-web/src/main/webapp/ui/ -type f  -name "*.js" -exec bash -c 'echo >>"$1"' _ {} \;
./gradlew deploy
