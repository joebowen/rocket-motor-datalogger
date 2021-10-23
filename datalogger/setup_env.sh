#!/bin/bash

sudo apt install qt5-default -y
pip3 install --user --no-input --upgrade setuptools wheel pip
pip3 install --user --no-input --upgrade -r requirements.txt
