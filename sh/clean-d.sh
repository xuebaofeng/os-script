#!/usr/bin/env bash
cd ${GRADLE_WORKSPACE}
#stop-services.sh
cw.sh
rm -rf tomcat-sfs/webapps/ROOT/
rm -rf .gradle-build-cache/
rm -rf .gradle/
rm -rf .idea/
rm -rf reports/
rm -rf build/
rm -rf gradle/
#rm -rf tomcat-sfs/sf_lib/
#rm -rf tomcat-sfs/sf_saml1_lib/
#rm -rf tomcat-sfs/sf_saml2_lib/
rm -rf tomcat-sfs/temp/
rm -rf tomcat-sfs/work/
find ${GRADLE_WORKSPACE}/au-V4 -name build -type d -exec rm -rf {} \;
find ${GRADLE_WORKSPACE}/build-system/ -name build -type d -exec rm -rf {} \;
