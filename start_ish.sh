#!/bin/bash
export DISPLAY=:0
cd /home/cleanish/dashish
source ~/ish/bin/activate
python ish.py >> /home/cleanish/dashish/ish.log 2>&1

