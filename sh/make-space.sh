rm -rf ~/.gradle/caches/modules-2/files-2.1/com.successfactors
rm -rf ~/.ivy2/cache/com.successfactors
rm -rf ~/.IdeaIC2016.2/system
rm -rf /data/sfsf/workspace/trunk/jboss-sfs
rm -rf /data/sfsf/workspace/trunk/tomcat-sfs
sudo find /data/sfsf/workspace -name target -exec rm -rf {} \;
sudo find /data/sfsf/workspace -name .gradle -exec rm -rf {} \;

