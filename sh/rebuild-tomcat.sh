#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/
gradle tomcatCleanSfs --stacktrace
gradle tomcatGenerateSfs --stacktrace
