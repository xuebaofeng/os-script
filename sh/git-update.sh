#!/usr/bin/env bash

date

echo '->pull main'

cd /Users/bxue/tlc/main
git pull


echo '->pull investor'
cd /Users/bxue/tlc/investor
git pull


echo '->pull lc-common'
cd /Users/bxue/tlc/lc-common
git pull


echo '->pull claw'
cd /Users/bxue/github/stock-claw
git pull



echo '->pull golang-web'
cd /Users/bxue/gowork/src/github.com/xuebaofeng/stock-web-golang/
git pull
