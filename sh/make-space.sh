#!/usr/bin/env bash
rm ~/java_error_in_IDEA.hprof

rm -rf ~/.IdeaIC2018.2
rm -rf ~/.gradle/caches
rm -rf ~/.ivy2/cache/com.successfactors

rm -rf ${GRADLE_WORKSPACE}/.gradle/

find ${GRADLE_WORKSPACE}/au-V4 -name build -type d -exec rm -rf {} \;
