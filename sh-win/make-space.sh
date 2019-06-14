#!/usr/bin/env bash
rm ~/java_error_in_IDEA.hprof

rm -rf ~/.IdeaIC2018.2
rm -rf ~/.gradle/caches
rm -rf ~/.ivy2/cache/com.successfactors

rm -rf /mnt/c/SAPDevelop/bizx/jboss-sfs
rm -rf /mnt/c/SAPDevelop/bizx/tomcat-sfs
rm -rf /mnt/c/SAPDevelop/bizx/.gradle/2.14.1
rm -rf /data/gradle/caches/modules-2/files-2.1/com.successfactors

find /mnt/c/SAPDevelop/bizx/au-V4 -name build -type d -exec rm -rf {} \;
