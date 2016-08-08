#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/build-system
svn update
cd /data/sfsf/workspace/trunk/au-V4
svn update
ant clean-deploy
start_jboss_pub_ram.sh
