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
function usage {
  echo "  -c,    Run Unit Test Cases"
  echo "  -t,    Create eon Tarball"
  echo "  -r,    Create eon RPM"
  echo "  -d,    Create eon DEBIAN"
  exit
}

create_rpm=0
create_tar=0
create_deb=0
run_tests=0

if [[ $# -eq 0 ]]
then
    usage
    exit 1
fi

while getopts "ctrd" OPTION
do
   case $OPTION in
      c)
         run_tests=1
         ;;
      t)
         create_tar=1
         ;;
      r)
         create_tar=1
         create_rpm=1
         ;;
      d)
         create_tar=1
         create_deb=1
         ;;
      ?)
         usage
         exit 1
         ;;
   esac
done


if [ $run_tests -eq 1 ]; then
    tox -epy26
    status=$?
    if [[ $status -ne 0 ]]
    then
      exit 1
    fi
fi

if [ $create_tar -eq 1 ]; then
  rm -rf eon/versioninfo
  python setup.py sdist
  status=$?
  if [[ $status -ne 0 ]]
  then
     echo "Error: Failed to create eon tar"
     exit 1
  else
     echo "Successfully created eon tar."
  fi
fi

if [ $create_rpm -eq 1 ]; then
    ver=`python rpm_util.py`
    rpmBuildPath=`pwd`/target/rpmbuild
    rm -rf $rpmBuildPath

    mkdir -p $rpmBuildPath/SOURCES
    cp dist/eon*.tar.gz $rpmBuildPath/SOURCES
    cp rpm/eon*.init $rpmBuildPath/SOURCES
    cp rpm/copyright $rpmBuildPath/SOURCES

    rpmbuild --define "_topdir $rpmBuildPath" --define "ver $ver" --define "release `date +%Y%m%d.%H%M%S`" -ba rpm/eon.spec
    status=$?
    if [[ $status -ne 0 ]]
    then
       echo "Error: Failed to create eon RPM"
       exit 1
    else
       echo "Successfully created eon RPM."
    fi
fi

if [ $create_deb -eq 1 ]; then
   tarPath=`pwd`/dist/eon-*.tar.gz
   python builddeb.py $tarPath "Changelog comments"
   status=$?
   if [[ $status -ne 0 ]]
   then
       echo "Error: Failed to create eon DEBIAN"
       exit 1
   else
       echo "Successfully created eon DEBIAN."
   fi
fi
