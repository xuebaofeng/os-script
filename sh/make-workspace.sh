#!/usr/bin/env bash
cd /data/sfsf/workspace
mkdir trunk
cd trunk
svn co http://svn.successfactors.com/repos/modules/V4/trunk au-V4
svn co http://svn.successfactors.com/repos/build-system/trunk build-system
cd build-system
gradle configureWorkspace

cp sfs-local-overrides/tomcat-dev-docker-oracle/build.properties ./