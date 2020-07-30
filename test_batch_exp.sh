#!/usr/bin/env bash

set -ex

for exp in {15..25}
do
  python3 -m cProfile -s cumtime qt_datalogger.py --debug --freq 2000 --batch-exp ${exp} --maxruntime 5 > tests/test-${exp}.csv
  sleep 20s
done