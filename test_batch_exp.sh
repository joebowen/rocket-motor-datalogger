#!/usr/bin/env bash

set -ex

for exp in {5..17}
do
  python3 -m cProfile qt_datalogger.py --freq 1000 --batch-exp ${exp} --maxruntime 5 > tests/test-${exp}.csv
done