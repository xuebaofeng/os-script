rm -rf ~/.gradle/caches
rm -rf ~/.ivy2/cache
rm -rf ~/.IdeaIC2016.2/system
rm -rf ~/.IdeaIC2016.3/system
rm -rf /data/sfsf/workspace/trunk/jboss-sfs
rm -rf /data/sfsf/workspace/trunk/tomcat-sfs
rm -rf /data/sfsf/workspace/trunk/.gradle/2.14.1

cd /data/
rm -rf flash_recovery
rm -rf .Trash-1004
cd sfsf
rm -rf eclipse_workspace
find /data/sfsf/workspace -name target -type d -exec rm -rf {} \;
