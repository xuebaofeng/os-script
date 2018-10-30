#!/usr/bin/env bash
rm ~/java_error_in_IDEA.hprof
rm -rf ~/.gradle/caches
rm -rf ~/.ivy2/cache/com.successfactors

rm -rf /data/sfsf/workspace/trunk/jboss-sfs
rm -rf /data/sfsf/workspace/trunk/tomcat-sfs
rm -rf /data/sfsf/workspace/trunk/.gradle/2.14.1
rm -rf /data/gradle/caches/modules-2/files-2.1/com.successfactors

find /data/sfsf/workspace/trunk/au-V4 -name build -type d -exec rm -rf {} \;
