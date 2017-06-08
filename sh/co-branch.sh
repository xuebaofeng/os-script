#!/usr/bin/env bash
if [ $# -eq 0 ]
  then
    echo "branch name?";
    exit 1;
fi

branch=$1

cd /data/sfsf/workspace

mkdir ${branch}
cd ${branch}

array=(V4 build-system)
for item in ${array[*]}
do
   echo "svn co http://svn.successfactors.com/repos/modules/${item}/branches/${branch} ${item}"
   svn co http://svn.successfactors.com/repos/modules/${item}/branches/${branch} ${item}
   cd ${item}
   svn cleanup
   svn update
   cd ..
done

cd ./build-system
gradle configureWorkspace

cp sfs-local-overrides/tomcat-dev-docker-oracle/build.properties ./