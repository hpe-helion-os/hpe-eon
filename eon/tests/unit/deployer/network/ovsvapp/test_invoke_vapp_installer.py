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

import contextlib

from mock import patch

from eon.deployer.network.ovsvapp.install.ovsvapp_installer_utility import (
    OVSvAppInstallerUtility)
from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.deployer.network.ovsvapp.install.vapp_installer import VappInstaller
from eon.deployer.network.ovsvapp.util.validate_inputs import ValidateInputs
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.deployer.util import VMwareUtils
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


class TestInvokeVappInstaller(tests.BaseTestCase):

    def setUp(self):
        super(TestInvokeVappInstaller, self).setUp()
        with contextlib.nested(
            patch.object(VMwareUtils, 'get_vcenter_session',
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, 'get_data_center',
                         return_value=fake_inputs.fake_datacenter)) as (
                mock_get_vcenter_session, mock_get_data_center):
            self.invoke_vapp_installer = \
                OVSvAppInstallerUtility(fake_inputs.data)
            self.assertTrue(mock_get_vcenter_session.called)
            self.assertTrue(mock_get_data_center.called)

    def test_setup_network(self):
        with contextlib.nested(
            patch.object(ValidateInputs, 'validate_inputs'),
            patch.object(NetworkAdapter, 'create_dvs_portgroup')) as (
                mock_validate_inputs, mock_create_dvs_portgroup):
            self.invoke_vapp_installer.setup_network()
            self.assertTrue(mock_validate_inputs.called)
            self.assertTrue(mock_create_dvs_portgroup.called)

    def test_invoke_ovsvapp_installer(self):
        vapps = {'Vapp-1': 'vapp-fake-1'}
        eon_dict = {'cluster_dvs_mapping': 'cluster1-dvs1',
                    'name': 'ovsvapp-1'}
        with contextlib.nested(
                patch.object(VMwareUtils, 'get_cluster',
                             return_value=fake_inputs.fake_clusters),
                patch.object(OVSvAppUtil, 'get_ovsvapps', return_value=vapps),
                patch.object(VappInstaller, 'run_installer',
                             return_value=eon_dict)) as (
                mock_get_cluster, mock_get_ovsvapps, mock_run_installer):
            output = self.invoke_vapp_installer.invoke_ovsvapp_installer()
            self.assertEqual(eon_dict, output)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_get_ovsvapps.called)
            self.assertTrue(mock_run_installer.called)
