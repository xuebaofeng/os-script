#!/usr/bin/env bash
cw.sh
cd ${GRADLE_WORKSPACE}/au-V4/au-V4-service/
gradle test --tests com.successfactors.proxy.*  

cd ${GRADLE_WORKSPACE}/au-V4/au-V4-ui/
gradle test --tests com.successfactors.proxy.*  
gradle test --tests com.successfactors.trial.ui.controller.guidedtour.GuidedTourControllerTest
gradle test --tests com.successfactors.user.ui.fb.FBAdminProxyMgtTest
