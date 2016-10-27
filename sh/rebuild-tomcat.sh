#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/
gradle cleanTomcatSfs --stacktrace
gradle generateTomcatSfs --stacktrace
