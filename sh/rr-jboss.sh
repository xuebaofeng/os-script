#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/
gradle deploy --stacktrace
restart-jboss.sh
