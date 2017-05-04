#!/bin/bash
#
# (c) Copyright 2015-2017 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

set -e

usage ()
{
    echo "-h: this help"
    echo "-f: do not use existing virtualenv"
    exit 0
}

# Change to the location of this script
cd "$( dirname "${BASH_SOURCE[0]}" )"

while getopts hf o
do
    case "$o" in
        f) echo "Deleting virtualenv..."; rm -rf .venv;;
        h) usage;;
        "?") usage; exit 0;;
    esac
done

# Create and activate the virtual environment
if [ -d ".venv" ]; then
    echo "Reusing existing virtual environment"
    source .venv/bin/activate
else
    echo "Creating new virtual environment"
    virtualenv .venv
    virtualenv --relocatable .venv
    source .venv/bin/activate
    pip -v --timeout=60 install -r tools/pip-requires -r tools/test-requires
    virtualenv --relocatable .venv
fi

# Execute the tests
export UNITTEST=yes

noseopts="$noseopts --with-xcoverage --cover-inclusive --cover-erase "
noseopts="$noseopts --with-xunit --cover-package=eon"
noseopts="$noseopts --ignore-files=oneview.py"
noseopts="$noseopts --ignore-files=setup.py"
nosetests $noseopts $noseargs eon

srcfiles=`find eon -type f -name "*.py"`
# Right now, we have chosen not to run pep8 and pylint on test source files.
# In the future, we may want to enable this and deal with all the issues in test files.
#srcfiles+=" `find tests -type f -name "*.py"`"
srcfiles+=" setup.py"

echo "Running pep8 ..."
# E262 is the warning that inline comments should have a space following the #.
# We must disable that check because pragma statements to control the coverage
# plugin require no space there.
pep8_opts="--ignore=W602,E501,E262,E12,E711,E721,E712,N303,N403,N404 --repeat"
pep8 ${pep8_opts} ${srcfiles} | tee pep8.txt > /dev/null

RETCODE=$?

# Clean up compiled code and coverage data
find . \( -name '*.pyc' -o -name '.pyo' -o -name ".coverage" \) -exec rm '{}' \;

exit $RETCODE
