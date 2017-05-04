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

import contextlib
import copy

from mock import patch

from eon.deployer.network.ovsvapp.cleanup.cleanup import Cleanup
from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.deployer.network.ovsvapp.install.vapp_installer import VappInstaller
from eon.deployer.network.ovsvapp.installer import OvsvappInstaller
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.deployer.util import VMwareUtils
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


class VmMap:

    def values(self):
        return ['ovsvapp1']


class TestOvsvappInstaller(tests.BaseTestCase):

    def setUp(self):
        super(TestOvsvappInstaller, self).setUp()
        self.ovsvapp_installer = OvsvappInstaller()
        self.cleanup = Cleanup

    def test_setup_network(self):
        with contextlib.nested(
            patch.object(NetworkAdapter, "_create_dvs"),
            patch.object(VMwareUtils, "get_vcenter_session",
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, "get_data_center",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(NetworkAdapter, "_create_dvpg"),
            patch.object(OvsvappInstaller, '_ovsvapp_input',
                         return_value=fake_inputs.data)) as (
                dvs_object, vmwareutil, ovsvapputil, mock_create_dvpg,
                mock_ovsvapp_input):
            inputs = copy.deepcopy(fake_inputs.data)
            self.ovsvapp_installer.setup_network(inputs)
            self.assertTrue(mock_ovsvapp_input.called)
            self.assertTrue(vmwareutil.called)
            self.assertTrue(ovsvapputil.called)
            self.assertTrue(dvs_object.called)
            self.assertTrue(mock_create_dvpg.called)

    def test_create(self):
        eon_dict = {}
        eon_dict['cluster_dvs_mapping'] = 'DC/host/cluster:Trunk-DVS'
        with contextlib.nested(
            patch.object(VMwareUtils, "get_cluster",
                         return_value=fake_inputs.fake_clusters),
            patch.object(OVSvAppUtil, "get_ovsvapps",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(VappInstaller, "run_installer",
                         return_value=eon_dict),
            patch.object(VMwareUtils, "get_vcenter_session",
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, "get_data_center",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(OvsvappInstaller, '_ovsvapp_input',
                         return_value=fake_inputs.data)) as (
                mock_get_cluster, mock_get_ovsvapp,
                mock_run_installer, mock_get_vecenter_session,
                mock_get_data_center, mock_ovsvapp_input):
            inputs = copy.deepcopy(fake_inputs.data)
            mock_result = self.ovsvapp_installer.create(inputs)
            self.assertTrue(mock_ovsvapp_input.called)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_get_ovsvapp.called)
            self.assertTrue(mock_run_installer.called)
            self.assertTrue(mock_get_vecenter_session.called)
            self.assertTrue(mock_get_data_center.called)
            self.assertEqual(mock_result, eon_dict)

    def test_update(self):
        pass

    def test_delete(self):
        with contextlib.nested(
            patch.object(VMwareUtils, "get_vcenter_session",
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, "get_data_center",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(VMwareUtils, "get_cluster",
                         return_value=fake_inputs.fake_clusters),
            patch.object(Cleanup, "_remove_affinity_rule"),
            patch.object(Cleanup, "_delete_ovsvapps_task"),
            patch.object(Cleanup, "_remove_cluster_vni_allocation"),
            patch.object(OvsvappInstaller, '_ovsvapp_input',
                         return_value=fake_inputs.data),
            patch.object(
                OVSvAppUtil, 'get_ovsvapps', return_value=VmMap())) as (
                mock_get_vcenter_session,
                mock_get_data_center, mock_get_cluster,
                mock_remove_affinity_rule,
                mock_delete_all_vapp,
                mock_remove_cluster,
                mock_ovsvapp_input,
                mock_get_ovsvapps):
            inputs = copy.deepcopy(fake_inputs.data)
            mock_delete_result = self.ovsvapp_installer.delete(inputs)
            self.assertTrue(mock_ovsvapp_input.called)
            self.assertEqual(True, mock_delete_result)
            self.assertTrue(mock_get_vcenter_session.called)
            self.assertTrue(mock_get_data_center.called)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_remove_affinity_rule.called)
            self.assertTrue(mock_delete_all_vapp.called)
            self.assertTrue(mock_remove_cluster.called)
            self.assertTrue(mock_get_ovsvapps.called)

    def test_tear_down_network(self):
        with contextlib.nested(
            patch.object(VMwareUtils, "get_vcenter_session",
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, "get_data_center",
                         return_value=fake_inputs.fake_datacenter),
            patch.object(VMwareUtils, "get_cluster",
                         return_value=fake_inputs.fake_clusters),
            patch.object(Cleanup, 'teardown_network'),
            patch.object(OvsvappInstaller, '_ovsvapp_input',
                         return_value=fake_inputs.data)) as (
                mock_get_vcenter_session, mock_get_data_center,
                mock_get_cluster, mock_teardown_network, mock_ovsvapp_input):
            inputs = copy.deepcopy(fake_inputs.data)
            self.ovsvapp_installer.teardown_network(inputs)
            self.assertTrue(mock_ovsvapp_input.called)
            self.assertTrue(mock_get_vcenter_session.called)
            self.assertTrue(mock_get_data_center.called)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_teardown_network.called)

    def test_get_info(self):
        # Will enable this after eon integration
        # self.assertIsNone(self.ovsvapp_installer.get_info("dummy_data"))
        pass
