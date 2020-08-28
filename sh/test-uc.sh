#!/usr/bin/env bash
set -e
cw.sh
cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-api/
gradle test --tests com.successfactors.upgradecenter.service.UCUpdateFeatureSetTest

cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-service/
gradle test --tests com.successfactors.upgradecenter.app.UpgradeCenterManagerTest
gradle test --tests com.successfactors.upgradecenter.util.deeplink.UpgradeCenterDetailsDeepLinkResolverTest
gradle test --tests com.successfactors.upgradecenter.utils.UpgradeCenterUtilsTest
gradle test --tests com.successfactors.upgradecenter.service.scheduledjob.UCUpgradeFeatureJobTest
gradle test --tests com.successfactors.upgradecenter.app.ActionStateManagerTest
gradle test --tests com.successfactors.ucxmlgenerator.app.UCFeatureXMLConfigManagerTest
gradle test
cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-service/
gradle integrationTest -Dunitils.configuration.localFileName=dit-hana.properties --tests com.successfactors.ucxmlgenerator.dao.impl.UCAnnouncementDAOImplTest
gradle integrationTest -Dunitils.configuration.localFileName=dit-hana.properties

cd ${GRADLE_WORKSPACE}/au-upgradecenter/au-upgradecenter-ui/
gradle test --tests com.successfactors.upgradecenter.ui.controller.utils.UpgradeCenterMediaServiceUtilsTest
gradle test --tests com.successfactors.upgradecenter.ui.controller.UpgradeCenterControllerTest
gradle test
