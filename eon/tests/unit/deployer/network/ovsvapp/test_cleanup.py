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
from pyVmomi import vim

from eon.deployer import util
from eon.deployer.network.ovsvapp.cleanup.cleanup import Cleanup
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.deployer.util import VMwareUtils
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


class OVSvapp:

    class runtime:
        powerState = 'poweredOn'

        class host:
            name = '10.10.10.10'

    def PowerOff(self):
        pass

    def ShutdownGuest(self):
        pass

    def Destroy(self):
        pass

    name = 'fake-name'


class VmMap:

    def values(self):
        return ['ovsvapp1']


class Network(vim.DistributedVirtualSwitch):

    def __init__(self):
        pass

    class summary:
        vm = None

    def Destroy_Task(self):
        pass

    name = 'net1'


class rules:

    name = 'fake-ovsvapp'
    key = 'key1'


class Cluster:

    class configuration:
        rule = [rules()]

    @staticmethod
    def ReconfigureComputeResource_Task(cluster_spec_ex, modify):
        pass


class TestCleanup(tests.BaseTestCase):

    def setUp(self):
        super(TestCleanup, self).setUp()
        self.ovs_vapp = {'name': 'fake-ovsvapp',
                         'obj': OVSvapp(),
                         'runtime.powerState': 'poweredOff',
                         'runtime.host': OVSvapp.runtime.host}
        self.cluster = {'obj': Cluster()}
        with contextlib.nested(
            patch.object(VMwareUtils, 'get_vcenter_session',
                         return_value=fake_inputs.MOB()),
            patch.object(VMwareUtils, 'get_data_center',
                         return_value=fake_inputs.fake_datacenter),
            patch.object(VMwareUtils, 'get_cluster',
                         return_value=self.cluster)) as (
                mock_get_vcenter_session, mock_get_data_center,
                mock_get_cluster):
            self.cleanup = Cleanup(fake_inputs.data)
            self.assertTrue(mock_get_vcenter_session.called)
            self.assertTrue(mock_get_data_center.called)
            self.assertTrue(mock_get_cluster.called)

    def test_destroy_network_task(self):
        with patch.object(util.VMwareUtils, 'wait_for_task') as (
                mock_wait_for_task):
            self.cleanup._destroy_network_task(Network())
            self.assertTrue(mock_wait_for_task.called)

    def test_poweroff_ovsvapp(self):
        self.ovs_vapp['runtime.powerState'] = 'poweredOn'
        with patch.object(VMwareUtils, 'wait_for_task')as (
                mock_wait_for_task):
            self.cleanup._poweroff_ovsvapp_task(self.ovs_vapp)
            self.assertTrue(mock_wait_for_task.called)

    def test_shutdown_ovsvapp(self):
        with patch.object(Cleanup, '_poweroff_ovsvapp_task') as (
                mock_poweroff_ovsvapp):
            self.cleanup._shutdown_ovsvapp_task(self.ovs_vapp)
            self.assertFalse(mock_poweroff_ovsvapp.called)

    def test_get_conf_ip(self):
        with contextlib.nested(
            patch.object(util, 'get_vmconfig_input'),
            patch.object(util, 'get_conf_pg'),
            patch.object(util.VMwareUtils, 'get_conf_network_details',
                         return_value=['10.10.10.10', ''])) as (
                mock_get_vmconfig_input, mock_get_conf_pg,
                mock_get_conf_network_details):
            output = self.cleanup._get_conf_ip(OVSvapp)
            self.assertEqual('10.10.10.10', output)
            self.assertTrue(mock_get_vmconfig_input.called)
            self.assertTrue(mock_get_conf_pg.called)
            self.assertTrue(mock_get_conf_network_details.called)

    def test_remove_affinity_rule(self):
        with patch.object(util.VMwareUtils, 'wait_for_task') as (
                mock_wait_for_task):
            self.cleanup._remove_affinity_rule([self.ovs_vapp])
            self.assertTrue(mock_wait_for_task.called)

    def test_delete_ovsvapps(self):
        with contextlib.nested(
            patch.object(Cleanup, '_get_conf_ip',
                         return_value='10.10.10.10'),
            patch.object(VMwareUtils, 'wait_for_task')) as (
                mock_get_conf_ip, mock_wait_for_task):
            output = self.cleanup._delete_ovsvapps_task(self.ovs_vapp)
            self.assertEqual('10.10.10.10', output)
            self.assertTrue(mock_get_conf_ip.called)
            self.assertTrue(mock_wait_for_task.called)

    def test_deactivate_cluster(self):
        with contextlib.nested(
            patch.object(OVSvAppUtil, 'get_ovsvapps',
                         return_value=VmMap()),
            patch.object(OVSvAppUtil, 'exec_multiprocessing')) as (
                mock_get_ovsvapps, mock_exec_multiprocessing):
            output = self.cleanup.deactivate_cluster()
            self.assertTrue(output)
            self.assertTrue(mock_get_ovsvapps.called)
            self.assertTrue(mock_exec_multiprocessing.called)
