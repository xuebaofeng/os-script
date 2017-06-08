#!/usr/bin/env bash
rm ~/java_error_in_IDEA.hprof
rm -rf ~/.gradle/caches
rm -rf ~/.ivy2/cache
rm -rf ~/.IdeaIC2016.2
rm -rf ~/.IdeaIC2016.3
rm -rf ~/.IdeaIC2017.1/system
rm -rf /usr/share/eclipse_4.5

cd /data/
rm -rf flash_recovery
rm -rf .Trash-1004
cd sfsf
rm -rf eclipse_workspace
find /data/sfsf/workspace -name target -type d -exec rm -rf {} \;
find /data/sfsf/workspace/trunk/V4 -name build -type d -exec rm -rf {} \;
find /data/sfsf/workspace/b1705/V4 -name build -type d -exec rm -rf {} \;
rm -rf /data/sfsf/workspace/trunk/V4/au-V4-service/build
rm -rf /data/sfsf/workspace/b1705/V4/au-V4-service/build

rm -rf /data/sfsf/workspace/trunk/jboss-sfs
rm -rf /data/sfsf/workspace/trunk/tomcat-sfs
rm -rf /data/sfsf/workspace/trunk/.gradle/2.14.1
rm -rf /data/gradle/caches/modules-2/files-2.1/com.successfactors