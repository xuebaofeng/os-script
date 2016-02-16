#!/usr/bin/env bash

git pull

cp ~/.zshrc ../dot/
cp ~/.gitconfig ../dot/
cp ~/.gitignore_global ../dot/
cp ~/.vimrc ../dot/

crontab -l > ../dot/.crontab
#crontab ../dot/.crontab

git add -A
git commit -m 'backup'
git push