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


cd /data/sfsf/workspace/trunk/bizx-docker-dev

#US East region	saas-docker-nsq.mo.sap.corp
#US West region	saas-docker-dub.mo.sap.corp
#Germany	saas-docker-rot.mo.sap.corp
export REGISTRY=saas-docker-nsq.mo.sap.corp

docker-compose pull ${database_type}

cd /data/sfsf/workspace/trunk
gradle upgradeTomcat --stacktrace  -Dargs="-devMode"
gradle migrateTomcat --stacktrace