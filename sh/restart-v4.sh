#!/usr/bin/env bash

database_type="oracle"

while getopts ":d:" opt; do
  case $opt in
    d) database_type="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

printf "Argument database_type is %s\n" "${database_type}"

start-${database_type}.sh
cd /data/sfsf/workspace/trunk
cp build-system/sfs-local-overrides/tomcat-dev-docker-${database_type}/build.properties build-system/
gradle tomcatUpdateSfs
cd tomcat-sfs/bin
./startSFS.sh
