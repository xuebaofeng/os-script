#!/bin/sh

#check if in trunk
CURRENT=$(pwd -P)
SF_TRUNK=/shared/gradle_workspace

do_build_system () {
    echo "STARTING .... "
    #BUILD_VERSION=$(curl -s http://repo.wdf.sap.corp:50000/repo/SuccessFactors/Operation/build/BIZX-SFV4/trunk.version |sed $'s/_/\\\n/g' | head -n 1)
    echo "Checking out build-system."
    cd $SF_TRUNK/build-system/

    git checkout master && git pull origin master
    git branch -D last_released
    git checkout tags/last-released/master -b last_released
    echo "checking out the latest tag"
    echo "Done with build-system"
}

do_release () {
    f=$1
    echo "Checking out $f"
    cd $SF_TRUNK/$f
    file=$SF_TRUNK/build-system/ivy-versions.properties
    version=$(cat $file |grep com.successfactors.$f.version=.* | sed $'s/=/\\\n/g' | tail -n 1)
    git fetch --tags
    git stash save -u
    git reset --hard
    git checkout master && git pull origin master
    git branch -d last_released

    echo git checkout tags/$version -b last_released
    git checkout tags/$version -b last_released
    cd $SF_TRUNK/$f
    git stash pop
    describe=$(git describe)
    echo "$f checkedout to $describe"
    cd $SF_TRUNK
}

if [ "$CURRENT" == "$SF_TRUNK" ]
then
    do_build_system
    cd $SF_TRUNK
    for k in idl-*; do
        if [ -d "$k" ]; then
            do_release $k
        fi
    done

    cd $SF_TRUNK
    for f in au-*; do
        if [ -d "$f" ]; then
            do_release $f
        fi
    done
else
    path=${PWD##*/}
    do_release $path
fi
