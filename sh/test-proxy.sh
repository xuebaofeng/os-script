#!/usr/bin/env bash
set -e
cw.sh
cd ${GRADLE_WORKSPACE}/au-V4/au-V4-service/
gradle test --tests com.successfactors.proxy.util.ProxyImportEventTest
gradle test --tests com.successfactors.proxy.bean.ProxyTimeBeanTest
gradle test --tests com.successfactors.proxy.*  


cd ${GRADLE_WORKSPACE}/au-V4/au-V4-ui/
gradle test --tests com.successfactors.user.ui.fb.FBAdminProxyMgtTest
gradle test --tests com.successfactors.proxy.*  
gradle test --tests com.successfactors.trial.ui.controller.guidedtour.GuidedTourControllerTest
