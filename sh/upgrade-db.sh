#!/usr/bin/env bash

cd /data/sfsf/workspace/trunk/bizx-docker-dev

#US East region	saas-docker-nsq.mo.sap.corp
#US West region	saas-docker-dub.mo.sap.corp
#Germany	saas-docker-rot.mo.sap.corp
export REGISTRY=saas-docker-dub.mo.sap.corp

docker-compose pull oracle

cd /data/sfsf/workspace/trunk
gradle upgradeTomcat
gradle migrateTomcat