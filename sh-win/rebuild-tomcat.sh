#!/usr/bin/env bash
cd /mnt/c/SAPDevelop/bizx/
./gradlew tomcatCleanSfs --stacktrace
./gradlew tomcatGenerateSfs --stacktrace
