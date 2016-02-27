set nocompatible              " be iMproved, required
filetype off                  " required

set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()

Plugin 'VundleVim/Vundle.vim'
Plugin 'ntpeters/vim-better-whitespace'
Plugin 'scrooloose/nerdtree'

call vundle#end()            " required
filetype plugin indent on    " required

:set encoding=UTF-8 expandtab tabstop=4 cursorline cursorcolumn number ruler title hlsearch laststatus=2 mouse=a background=dark
:syntax on
filetype indent on

