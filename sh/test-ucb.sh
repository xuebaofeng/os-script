#!/usr/bin/env bash
set -e
cw.sh
cd ${GRADLE_WORKSPACE}/idl-upgradecenterbase
gradle test
