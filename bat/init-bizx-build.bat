java8.bat
cd C:\SAPDevelop\bizx
rem git clone https://github.wdf.sap.corp/sfengservices/bizx-docker-dev.git
rem git clone https://github.wdf.sap.corp/bizx/build-system.git

cw.bat

cd ..
gradlew idea
gradlew tomcatGenerateSfs
gradlew deploy

