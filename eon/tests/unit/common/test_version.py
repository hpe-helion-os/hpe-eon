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

from oslo_config import cfg

from eon.common import version
import eon.tests.unit.tests as unit_tests

CONF = cfg.CONF


def fake_version_string():
    return "version"


def fake_release_string():
    return "1.0"


class TestVersion(unit_tests.BaseTestCase):

    def setUp(self):
        super(TestVersion, self).setUp()
        self.version_obj = version.VersionInfo("unit")

    def test_cached_version_string(self):
        self.version_obj.version_string = fake_version_string
        self.assertEqual("version", self.version_obj.cached_version_string())

    def test_version_string(self):
        self.version_obj.release_string = fake_release_string
        self.assertEqual("1.0", self.version_obj.version_string())
