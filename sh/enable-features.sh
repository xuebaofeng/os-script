#!/usr/bin/env bash
set -e
cd ${GRADLE_WORKSPACE}
xml=build-system/build/distributions/client/sfv4client.jar/sfv4client.xml
ant -f ${xml} runclient-tomcat -Dscript_class="com.successfactors.legacy.service.ejb.provisioning.ProvisioningClient" -Dscript_args="-enableFeatureForCompanies -c BizXTest -featureId 825"
