#!/usr/bin/env bash
cd /shared
rm -rf ./gradle_workspace
mkdir gradle_workspace
cd gradle_workspace
git clone https://github.wdf.sap.corp/sfengservices/bizx-docker-dev.git
git clone https://github.wdf.sap.corp/bizx/au-V4.git 
git clone https://github.wdf.sap.corp/bizx/build-system.git
cw.sh

