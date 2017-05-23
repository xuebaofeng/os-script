#!/usr/bin/env bash
cd /data/sfsf/workspace/trunk/build-system
svn cleanup
cd /data/sfsf/workspace/trunk/V4
svn cleanup

cd /data/sfsf/workspace/trunk
last_known_good up

#update_last_released.sh
