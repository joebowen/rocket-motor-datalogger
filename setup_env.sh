#!/bin/bash

sudo apt install qt5-default -y
sudo pip3 install --user --no-input --upgrade setuptools wheel pip
sudo pip3 install --user --no-input --upgrade -r requirements.txt
