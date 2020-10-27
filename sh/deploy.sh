#!/usr/bin/env bash
cw.sh
cd ${GRADLE_WORKSPACE}/
./gradlew deploy --stacktrace 
#-x tomcatUpdateSfs -x npmInstall
#./gradlew redeploy --rerun-tasks --no-build-cache
