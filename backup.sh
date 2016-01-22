#!/usr/bin/env bash

git pull

cp ~/.zshrc .zshrc
cp ~/.zshrc .zshrc
cp ~/.gitconfig .gitconfig
cp ~/.gitignore_global .gitignore_global

git add .
git commit -m 'backup'
git push