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
#.
from eon.virt.vmware import utils, constants

import eon.tests.unit.tests as unit_tests
from eon.tests.unit import fake_data
import copy


class TestCommonUtilsTestcase(unit_tests.BaseTestCase):
    def setUp(self):
        super(TestCommonUtilsTestcase, self).setUp()

    def tearDown(self):
        super(TestCommonUtilsTestcase, self).tearDown()

    def test_validate_vcenter_version_success(self):
        vc_version = "5.5"
        vc_build = "123456789"
        self.assertTrue(utils.validate_vcenter_version(vc_version, vc_build))

    def test_validate_vcenter_version_fail(self):
        vc_version = "4.5"
        vc_build = "123456"
        self.assertFalse(utils.validate_vcenter_version(vc_version, vc_build))

    def test_update_ova_template_info(self):
        expected = {'lifecycle_manager': {'hlm_version': '4.0.0'},
                    'template_info': {'upload_to_cluster': False},
                    'vm_config': [{'template_location': '',
                                   'template_name':
                                   'hlm-shell-vm-4.0.0-dc-1'}]}

        net_prop = copy.deepcopy(fake_data.network_prop)
        utils.update_ova_template_info(fake_data.cluster_data,
                                       net_prop)
        self.assertEqual(expected, net_prop)

    def test_update_ova_template_info_per_cluster(self):
        expected = {'lifecycle_manager': {'hlm_version': '4.0.0'},
                    'template_info': {'upload_to_cluster': True},
                    'vm_config': [{'template_location': '',
                                   'template_name':
                                   'hlm-shell-vm-4.0.0-cluster-1'}]}
        net_prop = copy.deepcopy(fake_data.network_prop)
        net_prop["template_info"][constants.UPLOAD_TO_CLUSTER] = True
        utils.update_ova_template_info(fake_data.cluster_data,
                                       net_prop)
        self.assertEqual(expected, net_prop)
