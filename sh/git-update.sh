#!/usr/bin/env bash

date

echo '->pull main'

cd ~/tlc/main
git pull


echo '->pull investor'
cd ~/tlc/investor
git pull


echo '->pull lc-common'
cd ~/tlc/lc-common
git pull


echo '->pull claw'
cd ~/github/stock-claw
git pull



echo '->pull golang-web'
cd ~/gowork/src/github.com/xuebaofeng/stock-web-golang/
git pull
