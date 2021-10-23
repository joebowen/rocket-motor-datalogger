#!/bin/bash

sudo curl https://raw.githubusercontent.com/KonradIT/gopro-linux/master/gopro -o /usr/local/bin/gopro
sudo chmod +x /usr/local/bin/gopro

sudo apt install -y mencoder libmagick++-dev

pip3 install --user --no-input --upgrade -r requirements.txt