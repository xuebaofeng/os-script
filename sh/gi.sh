#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}
gradle idea  -x npmInstall 
#-x websrcInstall
