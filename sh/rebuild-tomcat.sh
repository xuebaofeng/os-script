#!/usr/bin/env bash
cd ${bx_bizx_repo_path}/
./gradlew tomcatCleanSfs --stacktrace
./gradlew tomcatGenerateSfs --stacktrace
