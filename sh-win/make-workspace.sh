#!/usr/bin/env bash
cd /data/sfsf/workspace
rm -rf ./trunk
mkdir trunk
cd trunk
git clone https://github.wdf.sap.corp/sfengservices/bizx-docker-dev.git
git clone https://github.wdf.sap.corp/bizx/au-V4.git 
git clone https://github.wdf.sap.corp/bizx/build-system.git 
