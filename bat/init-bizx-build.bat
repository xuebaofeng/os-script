cd C:\wbem\github.wdf.sap.corp
git clone https://github.wdf.sap.corp/sfengservices/bizx-docker-dev.git
git clone https://github.wdf.sap.corp/bizx/build-system.git

cd build-system.git
gradlew -u configureWorkspace

cd ..
gradlew idea
gradlew tomcatGenerateSfs
gradlew deploy

