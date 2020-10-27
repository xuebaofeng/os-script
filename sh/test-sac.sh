#!/usr/bin/env bash
set -e
cw.sh
cd ${GRADLE_WORKSPACE}/idl-analytics-subjectarea/idl-analytics-subjectarea-service/
gradle test --tests com.successfactors.analytics.subject.schema.proxy.SACProxyAuditSubDomainSchemaBuilderTest
gradle test --tests com.successfactors.analytics.subject.schema.proxy.*


