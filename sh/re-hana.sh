#!/usr/bin/env bash

#sudo rm -rf /shared/docker-volumes/hana
docker stop bizx-docker-dev_hana_1
docker rm bizx-docker-dev_hana_1
docker container prune
#docker start bizx-docker-dev_hana_1
#docker load < /shared/k8s/bizx-database_hana-rmda.tar
start-services.sh
