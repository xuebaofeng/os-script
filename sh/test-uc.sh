#!/usr/bin/env bash
set -e
cw.sh
cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-service/
gradle test --tests com.successfactors.upgradecenter.utils.UpgradeCenterUtilsTest
gradle test --tests com.successfactors.upgradecenter.service.scheduledjob.UCUpgradeFeatureJobTest
gradle test --tests com.successfactors.upgradecenter.*
