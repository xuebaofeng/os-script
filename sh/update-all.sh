#!/usr/bin/env bash
update-svn.sh
cd /data/sfsf/workspace/trunk
gradle upgradeTomcat
gradle migrateTomcat