#!/usr/bin/env bash

git pull

cp ~/.zshrc .zshrc
cp ~/.gitconfig .gitconfig
cp ~/.gitignore_global .gitignore_global
cp ~/.vimrc .vimrc

git add .
git commit -m 'backup'
git push