#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/
gradle deploy --stacktrace

#rm /data/sfsf/workspace/trunk/tomcat-sfs/sf_lib/idl-schedulerservice-service-1.2.302.jar
#cp /data/sfsf/workspace/ant/schedulerservice/idl-schedulerservice-service/target/schedulerservice/package/idl-schedulerservice-service.jar /data/sfsf/workspace/trunk/tomcat-sfs/sf_lib/

~/restart-tomcat.sh
