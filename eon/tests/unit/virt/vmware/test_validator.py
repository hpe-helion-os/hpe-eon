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

from testtools import TestCase
from eon.virt.vmware import validator


class TestESXValidator(TestCase):
    @classmethod
    def setUpClass(self):
        TestCase.setUpClass()
        cluster_data1 = {"username": "UNSET",
             "name": "cluster name", "ip_address": "UNSET",
            "res_mgr_details": {},
            "inventory":
                {"datacenter": {"moid": "datacenter-1", "name": "dc"},
                  "hosts": [{"vms": "enabled"}], "DRS": ""},
             "id": "",
            "password": "password", "type": "esxcluster", "port": "UNSET",
            "host": "host1"}
        cluster_data2 = {"username": "UNSET",
             "name": "cluster name", "ip_address": "UNSET",
            "res_mgr_details": {},
            "inventory":
                {"datacenter": {"moid": "datacenter-1", "name": "dc"},
                  "hosts": [], "DRS": ""},
             "id": "",
            "password": "password", "type": "esxcluster", "port": "UNSET",
            "host": "host1"}
        self.val1 = validator.ESXValidator(cluster_data1)
        self.val2 = validator.ESXValidator(cluster_data2)

    def setUp(self):
        TestCase.setUp(self)

    def tearDown(self):
        TestCase.tearDown(self)

    def test_validate_names(self):
        self.assertRaises(Exception, self.val1.validate_names)

    def test_check_cluster_hosts(self):
        self.assertRaises(Exception, self.val2.check_cluster_hosts)

    def test_check_DRS_enabled(self):
        self.assertRaises(Exception, self.val1.check_DRS_enabled)
