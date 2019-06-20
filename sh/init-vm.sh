#!/usr/bin/env bash

#install sdkman, jenv
curl -s "https://get.sdkman.io" | bash
chown -R $(whoami) ~/.sdkman

cd ~
chown -R $(whoami) .

