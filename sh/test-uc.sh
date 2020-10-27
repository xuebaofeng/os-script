#!/usr/bin/env bash
set -e
cw.sh

cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-service/
gradle integrationTest -Dunitils.configuration.localFileName=dit-hana.properties

cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-ui/
gradle test

cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-service/
gradle test --tests com.successfactors.upgradecenter.bean.UpgradeCenterConfigTest
gradle test

