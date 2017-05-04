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

from mock import patch
from pyVmomi import vim

from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.deployer.util import VMwareUtils
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


# TODO: Put all the helper classes in one location
class PrepFolder:
    name = 'fake_folder'
    childEntity = False

    class MoveInto_Task:

        def __init__(self, val):
            self.val = val

    class Destroy_Task:
        pass


class MOB:

    class content():

        def rootFolder(self):
            pass

        def propertyCollector(self):
            pass


class VM:

    class Vm:

        class config:
            annotation = 'hp-ovsvapp'

        class runtime:
            powerState = 'poweredOn'

        class PowerOff:
            pass

        class Destroy:
            pass

    vm = [Vm]


class Cluster:

    @staticmethod
    def ReconfigureComputeResource_Task(cluster_spec_ex, modify):
        pass


class TestOVSvAppUtil(tests.BaseTestCase):

    def setUp(self):
        super(TestOVSvAppUtil, self).setUp()
        self.ovs_vapp_util = OVSvAppUtil()
        vc_info = fake_inputs.data.get('vcenter_configuration')
        self.cluster = {'obj': Cluster(),
                        'name': vc_info.get('cluster'),
                        'configuration.dasConfig.enabled': True,
                        'configuration.drsConfig.enabled': True}

    def test_get_ovsvapps(self):
        fake_vms = [{'name': 'ovsvapp_fake_vm',
                     'config.annotation': 'hp-ovsvapp',
                     'runtime.host': 'host-1'}]
        content = None
        vm_folder = None
        with contextlib.nested(
            patch.object(VMwareUtils, 'get_view_ref'),
            patch.object(VMwareUtils, 'collect_properties',
                         return_value=fake_vms))as (
                mock_get_view_ref, mock_collect_properties):
            output = self.ovs_vapp_util.get_ovsvapps(content, vm_folder,
                                                     fake_inputs.fake_clusters)
            self.assertEqual(fake_vms[0], output['host-1'])
            self.assertTrue(mock_get_view_ref.called)
            self.assertTrue(mock_collect_properties.called)

    def test_get_active_hosts(self):
        host = {'obj': 'host1', 'name': 'fake_host'}
        with patch.object(VMwareUtils, 'get_all_hosts',
                          return_value=[host]) as mock_get_all_hosts:
            self.ovs_vapp_util.get_active_hosts(MOB, 'vm_folder',
                                                ['host1'], 'cluster')
            self.assertTrue(mock_get_all_hosts.called)

    def test_exec_multiprocessing(self):
        pass

    def test_get_folder(self):
        pass

    def test_create_host_folder(self):
        with patch.object(OVSvAppUtil, '_get_folder',
                          return_value='fake_folder') as mock_get_folder:
            self.ovs_vapp_util.create_host_folder(
                'content', [{'cluster': {'name': self.cluster.get('name')}}],
                'host_folder')
            self.assertTrue(mock_get_folder.called)

    def test_move_hosts_in_to_folder(self):
        pass

    def test_enter_maintenance_mode(self):
        pass

    def test_destroy_failed_commissioned_vapps(self):
        host = {'obj': VM, 'name': 'fake_host'}
        with patch.object(VMwareUtils, 'wait_for_task') as mock_wait_for_task:
            self.ovs_vapp_util.destroy_failed_commissioned_vapps(host, MOB)
            self.assertTrue(mock_wait_for_task.called)

    def test_move_host_back_to_cluster(self):
        host = {'obj': 'host', 'name': 'fake_host'}
        cluster = {'obj': PrepFolder, 'name': 'fake_cluster'}
        with contextlib.nested(
                patch.object(OVSvAppUtil, 'destroy_failed_commissioned_vapps'),
                patch.object(OVSvAppUtil, 'enter_maintenance_mode'),
                patch.object(VMwareUtils, 'wait_for_task')) as (
                    mock_destroy, mock_enter_maintenance_mode,
                    mock_wait_for_task):
            self.ovs_vapp_util.move_host_back_to_cluster(MOB, host, cluster,
                                                         PrepFolder, 'err')
            self.assertTrue(mock_destroy.called)
            self.assertTrue(mock_enter_maintenance_mode.called)
            self.assertTrue(mock_wait_for_task.called)

    def test_get_host_parent(self):
        pass

    def test_get_cluster_inventory_path(self):
        pass

    def test_get_eon_env(self):
        pass

    def test_exec_subprocess(self):
        pass

    def test_disable_ha_on_ovsvapp(self):
        with contextlib.nested(
                patch.object(vim.VirtualMachine, '__init__',
                             return_value=None),
                patch.object(vim.HostSystem, '__init__', return_value=None),
                patch.object(VMwareUtils, 'wait_for_task')) as (
                    mock_vm, mock_host, mock_wait_for_task):
            vim.VirtualMachine.name = 'fake-vm'
            self.vm_obj = vim.VirtualMachine()
            self.host_obj = vim.HostSystem()
            host = {'obj': self.host_obj,
                    'name': 'fake_host'}
            self.ovs_vapp_util.disable_ha_on_ovsvapp(fake_inputs.session['si'],
                                                     self.vm_obj, self.cluster,
                                                     host)
            self.assertTrue(mock_vm.called)
            self.assertTrue(mock_host.called)
            self.assertTrue(mock_wait_for_task.called)
