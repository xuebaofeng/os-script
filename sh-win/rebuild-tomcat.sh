#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk//
./gradlew tomcatCleanSfs --stacktrace
./gradlew tomcatGenerateSfs --stacktrace
