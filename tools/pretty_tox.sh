#!/usr/bin/env bash

set -o pipefail

TESTRARGS=$1
python setup.py testr --slowest --testr-args="--subunit --concurrency 1 $TESTRARGS" | $(dirname $0)/subunit-trace.py --no-failure-debug -f
