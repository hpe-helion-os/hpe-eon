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

from eon.deployer.network.ovsvapp.install.dvs_adapter import DVSAdapter
from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs
from pyVmomi import vim


class network_folder:

    def find_by_name(self, name, entity_type=None):
        if (name == 'dvs-1' and entity_type == vim.DistributedVirtualSwitch):
            return True
        return False


class TestNetworkAdapter(tests.BaseTestCase):

    def setUp(self):
        super(TestNetworkAdapter, self).setUp()
        self.network_adapter = NetworkAdapter(fake_inputs.session,
                                              network_folder())
        self.port_groups = [{'name': 'fake-name', 'switchName': 'dvs-1'}]
        self.dvs = {'name': 'fake-name',
                    'mtu': 1500,
                    'physical_nics': 'nic1'}

    def test_create_dvs(self):
        with patch.object(DVSAdapter, 'create_dvs_skeleton') as (
                mock_create_dvs_skeleton):
            self.network_adapter._create_dvs(self.dvs)
            self.assertTrue(mock_create_dvs_skeleton.called)

    def test_create_dvpg(self):
        with patch.object(DVSAdapter, 'add_dv_port_groups') as (
                mock_add_dv_port_groups):
            self.network_adapter._create_dvpg(self.port_groups)
            self.assertTrue(mock_add_dv_port_groups.called)

    def test_configure_dvs(self):
        dvs = {'name': 'dvs-1',
               'mtu': 1500,
               'physical_nics': 'nic1'}
        with patch.object(DVSAdapter, 'reconfigure_dvs') as (
                mock_reconfigure_dvs):
            self.network_adapter._configure_dvs(dvs, 'hosts')
            self.assertTrue(mock_reconfigure_dvs.called)

    def test_configure_dvpg(self):
        with patch.object(DVSAdapter, 'reconfigure_dv_portgroup') as (
                mock_reconfigure_dv_portgroup):
            self.network_adapter._configure_dvpg(self.port_groups)
            self.assertTrue(mock_reconfigure_dv_portgroup.called)

    def test_create_dvs_portgroup(self):
        inputs = {'switches': [{'physical_nics': ['vmnic1']}],
                  'portGroups': ['pg1', 'pg2'],
                  'network_type': 'vlan'}
        with contextlib.nested(
            patch.object(NetworkAdapter, '_create_dvs'),
            patch.object(NetworkAdapter, '_create_dvpg')) as (
                mock_create_dvs, mock_create_dvpg):
            self.network_adapter.create_dvs_portgroup(inputs)
            self.assertTrue(mock_create_dvs.called)
            self.assertTrue(mock_create_dvpg.called)

    def test_configure_dvs_portgroup(self):
        inputs = {'switches': [{'physical_nics': []}],
                  'portGroups': ['pg1', 'pg2'],
                  'network_type': 'vxlan'}
        with contextlib.nested(
            patch.object(NetworkAdapter, '_create_dvs'),
            patch.object(NetworkAdapter, '_create_dvpg'),
            patch.object(NetworkAdapter, '_configure_dvs'),
            patch.object(NetworkAdapter, '_configure_dvpg')) as (
                mock_create_dvs, mock_create_dvpg,
                mock_configure_dvs, mock_configure_dvpg):
            self.network_adapter.configure_dvs_portgroup(inputs,
                                                         'hosts')
            self.assertTrue(mock_create_dvs.called)
            self.assertTrue(mock_create_dvpg.called)
            self.assertTrue(mock_configure_dvs.called)
            self.assertTrue(mock_configure_dvpg.called)
