#!/usr/bin/env bash
set -e
cw.sh
cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-service/
gradle test --tests com.successfactors.upgradecenter.utils.UpgradeCenterUtilsTest
gradle test --tests com.successfactors.upgradecenter.service.scheduledjob.UCUpgradeFeatureJobTest
gradle test --tests com.successfactors.upgradecenter.app.ActionStateManagerTest
gradle test --tests com.successfactors.upgradecenter.app.UpgradeCenterManagerTest
gradle test --tests com.successfactors.ucxmlgenerator.app.UCFeatureXMLConfigManagerTest
gradle test

cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-ui/
gradle test --tests com.successfactors.upgradecenter.ui.controller.UpgradeCenterControllerTest
gradle test
