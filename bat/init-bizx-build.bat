set JAVA_HOME=C:\wbem\sapjvm_8
set path=%JAVA_HOME%\bin;%path%
cd C:\wbem\bizx
rem git clone https://github.wdf.sap.corp/sfengservices/bizx-docker-dev.git
rem git clone https://github.wdf.sap.corp/bizx/build-system.git

cd build-system
start configureWorkspace

cd ..
gradlew idea
gradlew tomcatGenerateSfs
gradlew deploy

