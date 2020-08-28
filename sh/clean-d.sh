#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}
rm -rf .gradle-build-cache/
rm -rf .gradle/
rm -rf .idea/
rm -rf reports/
rm -rf build/
rm -rf gradle/
rm -rf tomcat-sfs/webapps/ROOT/
rm -rf tomcat-sfs/sf_lib/*
rm -rf build-system/build/
rm -rf build-system/.gradle/
rm -rf au-V4/au-V4-ui/build/
rm -rf au-V4/au-V4-web/build/
rm -rf au-V4/au-V4-service/build/
rm -rf au-upgradecenter/au-upgradecenter-ui/build/
rm -rf au-upgradecenter/au-upgradecenter-web/build/
rm -rf au-upgradecenter/au-upgradecenter-service/build/
rm -rf au-upgradecenter/au-upgradecenter-dependencies/
yes | cp ./build-system/sfs-local-overrides/tomcat-dev-docker-hana/gradle-local.properties ./build-system/gradle/properties/
#rr-v4.sh
