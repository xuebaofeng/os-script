rm -rf ~/.gradle/caches/modules-2/files-2.1/com.successfactors
rm -rf ~/.ivy2/cache/com.successfactors
rm -rf ~/.IdeaIC2016.2/system
rm -rf /data/sfsf/workspace/trunk/jboss-sfs
rm -rf /data/sfsf/workspace/trunk/tomcat-sfs
cd /data/
rm -rf flash_recovery
rm -rf .Trash-1004
cd sfsf
rm -rf eclipse_workspace

find /data/sfsf/workspace -name target -type d -exec rm -rf {} \;