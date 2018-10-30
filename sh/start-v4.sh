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
start-zookeeper.sh

cd /data/sfsf/workspace/trunk
cp -r build-system/sfs-local-overrides/tomcat-dev-docker-${database_type}/* tomcat-sfs
cd tomcat-sfs/bin
./startSFS.sh
