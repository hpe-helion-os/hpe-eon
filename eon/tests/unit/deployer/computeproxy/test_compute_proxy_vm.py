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

import eon.deployer.computeproxy.compute_proxy_vm as ComputeProxyVm
from eon.common import log
from eon.deployer import util
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs

LOG = log.getLogger('eon.deployer.computeproxy.compute_proxy_vm')


class VM:
    name = 'fake_vm'

    class Destroy:
        pass

    class PowerOff:
        pass

    class ShutdownGuest:
        pass

    class runtime:
        powerState = 'poweredOff'

    class guest:

        class net_attr:
            network = 'PG-1'
            macAddress = 'ff:ff:ff:ff:ff'
            ipAddress = '10.10.10.10'

        net = [net_attr, net_attr, net_attr]


class MOB:

    class content:

        class rootFolder:

            def find_by_name(self, vm_name):
                pass

        class viewManager:
            pass


class TestCompute_proxy_vm(tests.BaseTestCase):

    def setUp(self):
        super(TestCompute_proxy_vm, self).setUp()
        self.session = {'content': MOB.content(), 'si': 'session_intance'}

    def test_get_vm_location_details(self):
        cluster = {'name': 'cluster-1', 'obj': 'cluster-obj'}
        with contextlib.nested(
                patch.object(util.VMwareUtils, 'get_data_center'),
                patch.object(util.VMwareUtils, 'get_cluster',
                             return_value=cluster),
                patch.object(ComputeProxyVm, 'get_one_active_host_for_cluster',
                             return_value={'name': 'host1'}),
                patch.object(
                    util.VMwareUtils, 'get_shared_datastore',
                    return_value='SDC-1')) as (
                        mock_get_data_center, mock_get_cluster,
                        mock_get_active_host, mock_get_shared_datastore):
            output = ComputeProxyVm.get_vm_location_details(MOB.content,
                                                            'DC-1',
                                                            'cluster-0123')
            self.assertEqual(cluster, output['cluster'])
            self.assertEqual({'cluster': cluster, 'name': 'host1'},
                             output['host'])
            self.assertTrue(mock_get_data_center.called)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_get_active_host.called)
            self.assertTrue(mock_get_shared_datastore.called)

    def test_get_vmconf(self):
        vmconfig = {"cpu": 2, "memory_in_mb": 1024}
        nics = [{'type': 'pcipt'}]
        vmconfig['nics'] = nics
        devices = []
        vmconf = util.VMwareUtils().get_vm_config(vmconfig, devices)
        self.assertEqual(2, vmconf.numCPUs)
        self.assertEqual(1024, vmconf.memoryMB)
        self.assertEqual(1024, vmconf.memoryAllocation.reservation)
        self.assertEqual(True, vmconf.memoryReservationLockedToMax)

    def test_clone_shell_vm(self):
        pass

    def test_attach_nic_to_vm(self):
        pass

    def test_power_on_vm(self):
        pass

    def test_power_off_vm(self):
        with patch.object(util.VMwareUtils, 'wait_for_task',
                          return_value=None) as mock_wait_for_task:
            output = ComputeProxyVm.power_off_vm(VM, fake_inputs.session)
            self.assertEqual(True, output)
            self.assertTrue(mock_wait_for_task.called)

    def test_delete_vm(self):
        with patch.object(util.VMwareUtils, 'wait_for_task',
                          return_value=None) as mock_wait_for_task:
            ComputeProxyVm.delete_vm(VM, self.session)
            self.assertTrue(mock_wait_for_task.called)

    def test_create_shell_vm_if_vm_present(self):
        with contextlib.nested(
                patch.object(ComputeProxyVm, 'get_vm_location_details'),
                patch.object(util.VMwareUtils, 'get_vm')) as (
                    mock_get_vm_location_details, mock_get_vm):
            ComputeProxyVm.create_shell_vm(self.session, VM.name,
                                           fake_inputs.data)
            self.assertTrue(mock_get_vm_location_details.called)
            self.assertTrue(mock_get_vm.called)

    def test_create_shell_vm(self):
        with patch.object(vim.VirtualMachine, '__init__',
                          return_value=None) as mock_constructor:
            self.vm_obj = vim.VirtualMachine()
            self.assertTrue(mock_constructor.called)

        with contextlib.nested(
                patch.object(ComputeProxyVm, 'get_vm_location_details'),
                patch.object(util.VMwareUtils, 'get_vm', return_value=None),
                patch.object(util.VMwareUtils, 'get_template'),
                patch.object(util.VMwareUtils, 'get_virtual_devices'),
                patch.object(util.VMwareUtils, 'get_vm_config'),
                patch.object(util.VMwareUtils, 'get_relocation_spec'),
                patch.object(util.VMwareUtils, 'clone_vm',
                             return_value=self.vm_obj),
                patch.object(util, 'get_conf_pg'),
                patch.object(util.SharedIPAllocator, 'get_ips'),
                patch.object(util.ServiceVMCustomizer, 'customize_service_vm'),
                patch.object(ComputeProxyVm, 'get_shell_vm_info')) as (
                    mock_get_vm_location_details, mock_get_vm,
                    mock_get_template, mock_get_virtual_devices,
                    mock_get_vm_config, mock_get_relocation_spec,
                    mock_clone_vm, mock_get_conf_pg, mock_get_ips,
                    mock_customize_service_vm, mock_get_shell_vm_info):
            ComputeProxyVm.create_shell_vm(self.session, VM.name,
                                           fake_inputs.data)
            self.assertTrue(mock_get_vm_location_details.called)
            self.assertTrue(mock_get_vm.called)
            self.assertTrue(mock_get_template.called)
            self.assertTrue(mock_get_virtual_devices.called)
            self.assertTrue(mock_get_vm_config.called)
            self.assertTrue(mock_get_relocation_spec.called)
            self.assertTrue(mock_clone_vm.called)
            self.assertTrue(mock_get_conf_pg.called)
            self.assertTrue(mock_get_ips.called)
            self.assertTrue(mock_customize_service_vm.called)
            self.assertTrue(mock_get_shell_vm_info.called)

    def test_create_shell_vm_failure(self):
        with patch.object(vim.VirtualMachine, '__init__',
                          return_value=None) as mock_constructor:
            self.vm_obj = vim.VirtualMachine()
            self.assertTrue(mock_constructor.called)

        with contextlib.nested(
                patch.object(ComputeProxyVm, 'get_vm_location_details'),
                patch.object(util.VMwareUtils, 'get_vm', return_value=None),
                patch.object(util.VMwareUtils, 'get_template'),
                patch.object(util.VMwareUtils, 'get_virtual_devices'),
                patch.object(util.VMwareUtils, 'get_vm_config'),
                patch.object(util.VMwareUtils, 'get_relocation_spec'),
                patch.object(util.VMwareUtils, 'clone_vm',
                             return_value=self.vm_obj),
                patch.object(util, 'get_conf_pg'),
                patch.object(util.SharedIPAllocator, 'get_ips'),
                patch.object(ComputeProxyVm, 'get_shell_vm_info'),
                patch.object(util.SharedIPAllocator, 'release_ips'),
                patch.object(ComputeProxyVm, 'delete_shell_vm'),
                patch.object(LOG, 'exception')) as (
                    mock_get_vm_location_details, mock_get_vm,
                    mock_get_template, mock_get_virtual_devices,
                    mock_get_vm_config, mock_get_relocation_spec,
                    mock_clone_vm, mock_get_conf_pg, mock_get_ips,
                    mock_get_shell_vm_info, mock_release_ips,
                    mock_delete_shell_vm, mock_log):
            self.assertRaises(TypeError,
                              lambda: ComputeProxyVm.create_shell_vm(
                                        self.session, VM.name,
                                        fake_inputs.data))
            self.assertTrue(mock_get_vm_location_details.called)
            self.assertTrue(mock_get_vm.called)
            self.assertTrue(mock_get_template.called)
            self.assertTrue(mock_get_virtual_devices.called)
            self.assertTrue(mock_get_vm_config.called)
            self.assertTrue(mock_get_relocation_spec.called)
            self.assertTrue(mock_clone_vm.called)
            self.assertTrue(mock_get_conf_pg.called)
            self.assertTrue(mock_get_ips.called)
            self.assertFalse(mock_get_shell_vm_info.called)
            self.assertTrue(mock_release_ips.called)
            self.assertTrue(mock_delete_shell_vm.called)
            self.assertTrue(mock_log.called)

    def test_delete_shell_vm(self):
        with contextlib.nested(
            patch.object(ComputeProxyVm, 'delete_vm'),
            patch.object(util.VMwareUtils, 'get_conf_network_details',
                         return_value=['10.10.10.10', '']),
            patch.object(MOB.content.rootFolder, 'find_by_name',
                         return_value=VM)) as (
                mock_delete_vm,
                mock_get_conf_network_details, mock_find_by_name):
            ComputeProxyVm.delete_shell_vm(self.session, 'vm_name', 'force')
            self.assertTrue(mock_delete_vm.called)
            self.assertTrue(mock_get_conf_network_details.called)
            self.assertTrue(mock_find_by_name.called)

    def test_get_shell_vm_info(self):
        with contextlib.nested(
                patch.object(util.VMwareUtils, 'get_conf_ip_and_mac',
                             return_value=['10.10.10.10',
                                           'ff:ff:ff:ff:ff']),
                patch.object(
                    MOB.content.rootFolder, 'find_by_name',
                    return_value=VM)) as (mock_get_conf_ip_and_mac,
                                          mock_find_by_name):
            output = ComputeProxyVm.get_shell_vm_info(self.session,
                                                      'fake_vm', 'trunk')
            self.assertEqual('ff:ff:ff:ff:ff', output['pxe-mac-addr'])
            self.assertEqual('10.10.10.10', output['pxe-ip-addr'])
            self.assertEqual('fake_vm', output['name'])
            self.assertTrue(mock_get_conf_ip_and_mac.called)
            self.assertTrue(mock_find_by_name)

    def test_shut_down_vm(self):
        output = ComputeProxyVm.shut_down_vm(VM, fake_inputs.session)
        self.assertEqual(True, output)

    def test_get_active_host(self):
        fake_hosts = [{'name': 'host1',
                       'summary.runtime.powerState': 'poweredOff',
                       'summary.runtime.inMaintenanceMode': False},
                      {'name': 'host2',
                       'summary.runtime.powerState': 'poweredOn',
                       'summary.runtime.inMaintenanceMode': False},
                      {'name': 'host3',
                       'summary.runtime.powerState': 'poweredOn',
                       'summary.runtime.inMaintenanceMode': True}]
        with patch.object(util.VMwareUtils, 'get_all_hosts',
                          return_value=fake_hosts) as mock_get_all_hosts:
            output = ComputeProxyVm.get_one_active_host_for_cluster('si',
                                                                    'clusters')
            self.assertEqual('host2', output['name'])
            self.assertEqual(False,
                             output['summary.runtime.inMaintenanceMode'])
            self.assertEqual('poweredOn', output['summary.runtime.powerState'])
            self.assertTrue(mock_get_all_hosts.called)
