#!/usr/bin/env bash
cd /mnt/c/wbem/bizx/
./gradlew tomcatCleanSfs --stacktrace
./gradlew tomcatGenerateSfs --stacktrace
