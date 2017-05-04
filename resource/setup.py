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

import setuptools
from eon.common import setup

requires = setup.parse_requirements()
depend_links = setup.parse_dependency_links()
project = 'eon'

setuptools.setup(
    name=project,
    version='${release.version}',
    description='The Eon project provides services for '
                'registering, and retrieving of Vcenters, clusters.',
    author='Pulsar',
    author_email='hpcloud@hp.com',
    url='http://www.hp.com/',
    packages=setuptools.find_packages(exclude=['bin']),
    test_suite='nose.collector',
    cmdclass=setup.get_cmdclass(),
    include_package_data=True,
    install_requires=requires,
    dependency_links=depend_links,
    scripts=['bin/eon-api',
             'bin/eon-conductor',
        'bin/eon-manage'],
    py_modules=[])
