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

from eon.tests.unit import tests
from eon.deployer.computeproxy.cp_utility import ProxyInstallerUtility
from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.deployer.network.ovsvapp.cleanup.cleanup import Cleanup
from eon.deployer.util import VMwareUtils
from eon.tests.unit.deployer import fake_inputs


class TestProxyInstallerUtility(tests.BaseTestCase):

    def setUp(self):
        super(TestProxyInstallerUtility, self).setUp()

    def test_create_network_infra(self):
        with contextlib.nested(
            patch.object(VMwareUtils, "get_vcenter_session",
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, "get_data_center",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(NetworkAdapter, "_create_dvs"),
            patch.object(NetworkAdapter, "_create_dvpg"),
        ) as (mock_vc_session, mock_get_dc, mock_create_dvs, mock_create_dvpg):
            proxy_utility = ProxyInstallerUtility(fake_inputs.data)
            proxy_utility.create_network_infrastructure()
            self.assertTrue(mock_vc_session.called)
            self.assertTrue(mock_get_dc.called)
            self.assertTrue(mock_create_dvs.called)
            self.assertTrue(mock_create_dvpg.called)

    def test_configure_network_infra(self):
        with contextlib.nested(
            patch.object(VMwareUtils, "get_vcenter_session",
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, "get_data_center",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(VMwareUtils, "get_cluster"),
            patch.object(VMwareUtils, "get_all_hosts"),
            patch.object(NetworkAdapter, "_create_dvs"),
            patch.object(NetworkAdapter, "_create_dvpg"),
            patch.object(NetworkAdapter, "_configure_dvs"),
            patch.object(NetworkAdapter, "_configure_dvpg"),
        ) as (mock_vc_session, mock_get_dc, mock_get_cluster,
              mock_get_all_hosts, mock_create_dvs, mock_create_dvpg,
              mock_configure_dvs, mock_configure_dvpg):
            proxy_utility = ProxyInstallerUtility(fake_inputs.data)
            proxy_utility.configure_network_infrastructure()
            self.assertTrue(mock_vc_session.called)
            self.assertTrue(mock_get_dc.called)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_get_all_hosts.called)
            self.assertTrue(mock_create_dvs.called)
            self.assertTrue(mock_create_dvpg.called)
            self.assertTrue(mock_configure_dvs.called)
            self.assertTrue(mock_configure_dvpg.called)

    def test_teardown_network(self):
        with contextlib.nested(
            patch.object(VMwareUtils, "get_vcenter_session",
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, "get_data_center",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(VMwareUtils, "get_cluster"),
            patch.object(Cleanup, 'teardown_network'),
        ) as (mock_vc_session, mock_get_dc, mock_get_cluster,
              mock_teardown_net):
            proxy_utility = ProxyInstallerUtility(fake_inputs.data)
            proxy_utility.teardown_network(fake_inputs.data)
            self.assertTrue(mock_vc_session.called)
            self.assertTrue(mock_get_dc.called)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_teardown_net.called)
