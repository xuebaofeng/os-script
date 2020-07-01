#!/usr/bin/env bash
cw.sh
yes | cp ${GRADLE_WORKSPACE}/build-system/sfs-local-overrides/tomcat-dev-docker-hana/gradle-local.properties ${GRADLE_WORKSPACE}/build-system/gradle/properties/
cd ${GRADLE_WORKSPACE}/
./gradlew --stop
./gradlew clean
./gradlew redeploy --stacktrace --profile --info
