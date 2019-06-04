#!/usr/bin/env bash
cd /mnt/c/wbem/bizx/
find ./au-V4/au-V4-web/src/main/webapp/ui/ -type f  -name "*.js" -exec bash -c 'echo >>"$1"' _ {} \;
./gradlew deploy