#!/usr/bin/env bash
rm ~/java_error_in_IDEA.hprof

rm -rf ~/.IdeaIC2018.2
rm -rf ~/.gradle/caches
rm -rf ~/.ivy2/cache/com.successfactors

rm -rf ${GRADLE_WORKSPACE}/jboss-sfs
rm -rf ${GRADLE_WORKSPACE}/tomcat-sfs
rm -rf ${GRADLE_WORKSPACE}/.gradle/2.14.1
rm -rf /data/gradle/caches/modules-2/files-2.1/com.successfactors

find ${GRADLE_WORKSPACE}/au-V4 -name build -type d -exec rm -rf {} \;
