#!/usr/bin/env bash
sudo lsof -i:30015


#docker-pr 1978 root    4u  IPv4  36422      0t0  TCP localhost:30015 (LISTEN)
#saas-docker-dub.mo.sap.corp/bizx-database/hana-rmda:trunk.weekly   "/init.sh"          14 minutes ago      Up 2 minutes        127.0.0.1:30015->30015/tcp   bizx-docker-dev_hana_1
