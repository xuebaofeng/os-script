#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/build-system
svn update --username I854966
cd /data/sfsf/workspace/trunk/au-V4
svn update --username I854966
rebuild-tomcat.sh
#~/rebuild-jboss.sh
rr-tomcat.sh
#~/rr-jboss.sh
