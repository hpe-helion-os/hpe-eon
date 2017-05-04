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
'''
Created on Jun 26, 2015

@author: dpadi
'''

from eon.tests.unit import tests
from eon.deployer import basedriver


class TestBaseDriver(tests.BaseTestCase):

    def setUp(self):
        super(TestBaseDriver, self).setUp()
        self.base_driver = basedriver.BaseDriver()

    def test_base_driver(self):
        self.assertIsInstance(self.base_driver, basedriver.BaseDriver)

    def test_create(self):
        self.assertRaises(NotImplementedError,
                          self.base_driver.create, "dummy_data")

    def test_update(self):
        self.assertRaises(NotImplementedError,
                          self.base_driver.update, "dummy_data")

    def test_delete(self):
        self.assertRaises(NotImplementedError,
                          self.base_driver.delete, "dummy_data")

    def test_get_info(self):
        self.assertRaises(NotImplementedError,
                          self.base_driver.get_info, "dummy_data")
