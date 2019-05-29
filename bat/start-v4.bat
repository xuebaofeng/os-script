cd C:\wbem\github.wdf.sap.corp\bizx-docker-dev
docker-compose up -d oracle
docker-compose up -d zookeeper

cd ..
gradlew tomcatStartSfs