#!/bin/sh

git_pull () {
    f=$1
    echo "Checking out $f"
    cd ${GRADLE_WORKSPACE}/$f
    git fetch --tags
    git stash save -u
    git reset --hard
    git checkout master && git pull origin master
    git stash pop
    cd ${GRADLE_WORKSPACE}
}

cd ${GRADLE_WORKSPACE}
for k in idl-*; do
    if [ -d "$k" ]; then
        git_pull $k
    fi
done

cd ${GRADLE_WORKSPACE}
for f in au-*; do
    if [ -d "$f" ]; then
        git_pull $f
    fi
done
