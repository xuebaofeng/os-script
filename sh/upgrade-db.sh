#!/usr/bin/env bash
cd ${bx_bizx_repo_path}/
./gradlew upgradeTomcat --stacktrace  -Dargs="-devMode"
./gradlew migrateTomcat --stacktrace
