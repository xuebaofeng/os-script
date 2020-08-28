#!/usr/bin/env bash
cw.sh
cd ${GRADLE_WORKSPACE}/
./gradlew deploy --stacktrace -x :build-system:tomcatUpdateSfs

#./gradlew redeploy --rerun-tasks --no-build-cache
