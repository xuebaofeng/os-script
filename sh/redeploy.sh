#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/build-system
gradle -u configureWorkspace
cd /data/sfsf/workspace/trunk/
gradle --profile redeploy --stacktrace
