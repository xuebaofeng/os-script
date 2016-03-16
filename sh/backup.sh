#!/usr/bin/env bash

cd ~/github/os-script
git pull

cp ~/.zshrc ./dot/
cp ~/.gitconfig ./dot/
cp ~/.gitignore_global ./dot/
cp ~/.vimrc ./dot/

crontab -l > ./dot/.crontab

git add -A
git commit -m 'backup'
git push
