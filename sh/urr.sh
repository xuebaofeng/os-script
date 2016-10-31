#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/build-system
svn update
cd /data/sfsf/workspace/trunk/au-V4
svn update
rr-tomcat.sh
#~/rr-jboss.sh
