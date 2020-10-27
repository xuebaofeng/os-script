#!/usr/bin/env bash
if [ $# -gt 0 ]; then
    echo "Your command line contains $# arguments"
else
    echo "Input the repo name, like 'au-V4'"
    exit 1;
fi
cd ${GRADLE_WORKSPACE}/
git clone https://github.wdf.sap.corp/bizx/$1.git
gi.sh
