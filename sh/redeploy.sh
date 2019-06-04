#!/usr/bin/env bash
cd /mnt/c/wbem/bizx/build-system
./configureWorkspace
cd /mnt/c/wbem/bizx/
./gradlew redeploy --stacktrace
