#!/usr/bin/env bash
cw.sh
yes | cp ${bx_bizx_repo_path}/build-system/sfs-local-overrides/tomcat-dev-docker-hana/gradle-local.properties ${bx_bizx_repo_path}/build-system/gradle/properties/
cd ${bx_bizx_repo_path}/
#./gradlew --stop
#./gradlew clean
#./gradlew redeploy --stacktrace
./gradlew deploy
