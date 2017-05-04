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
import os

from mock import patch
from pyVmomi import vim

import eon.common.log as logging
from eon.deployer import util
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs

LOG = logging.getLogger('eon.deployer.util')


class host:

    class summary:

        class runtime:
            powerState = 'poweredOn'
            inMaintenanceMode = False

    class configManager:

        class storageSystem:

            class storageDeviceInfo:

                class scsi_lun:
                    model = 'Virtual disk'
                scsiLun = [scsi_lun]


class PCI:

    class pciDevice:
        id = '04:00.0'
        deviceId = 1234
        vendorId = 1223

    class device:
        pass

    systemId = '56974866-3d8e-37f0-74d9-9457a5537d1c'


def _gb2byte(size):
    return size * 1024 * 1024 * 1024


class DataStore:

    class summary:
        type = 'NFS'
        accessible = True
        maintenanceMode = False
        freeSpace = _gb2byte(160)


class MOB:

    def __init__(self):
        pass

    def RetrieveContent(self):
        pass

    class content():

        def rootFolder(self):
            pass

        class propertyCollector:

            class RetrieveContents:
                pass

        class viewManager:

            class CreateContainerView:

                def __init__(self, **kwargs):
                    pass


class NicInfo:
    network = 'TRUNK'
    ipAddress = ['10.10.10.20']
    macAddress = 'aa:bb:cc:dd:ee:ff'


net1 = NicInfo()
net2 = copy.deepcopy(net1)
net2.network = None
net2.ipAddress = ['10.10.10.30']
net2.macAddress = 'aa:bb:cc:dd:ee:fg'

net3 = copy.deepcopy(net1)
net3.network = 'ESX-Conf'
net3.ipAddress = ['10.10.10.40']
net3.macAddress = 'aa:bb:cc:dd:ee:fh'


class VM:

    class guest:
        toolsStatus = 'toolsOk'
        net = [net1, net2, net3]


class PrepFolder:
    pass


class TestUtil(tests.BaseTestCase):

    def setUp(self):
        super(TestUtil, self).setUp()
        self.shared_ip_obj = util.SharedIPAllocator()
        self.vmware_util = util.VMwareUtils()

    def test_get_ips(self):
        with contextlib.nested(
            patch.object(util, 'load_json_data',
                         return_value=[]),
            patch.object(util.SharedIPAllocator, '_store_ips',
                         return_value=[])) as (
                mock_load_json_data, mock_store_ips):
            output = self.shared_ip_obj.get_ips('10.0.0.0/24', '10.0.0.0',
                                                '10.0.0.255', '10.0.0.1', 254)
            self.assertIn('10.0.0.0', output)
            self.assertNotIn('10.0.0.1', output)
            self.assertNotIn('10.0.0.255', output)
            self.assertIn('10.0.0.254', output)
            self.assertTrue(mock_load_json_data.called)
            self.assertTrue(mock_store_ips.called)

    def test_get_ip_list(self):
        output = self.shared_ip_obj._get_ip_list('10.0.0.0/24', '10.0.0.0',
                                                 '10.0.0.255', '10.0.0.1')
        self.assertIn('10.0.0.0', output)
        self.assertNotIn('10.0.0.1', output)
        self.assertIn('10.0.0.255', output)
        self.assertIn('10.0.0.254', output)

    def test_release_ips(self):
        fake_ip_catalog = ['10.0.0.2', '10.0.0.3', '10.0.0.4']
        with contextlib.nested(
            patch.object(util, 'load_json_data',
                         return_value=fake_ip_catalog),
            patch.object(os.path, 'isfile',
                         return_value=True)) as (
                mock_load_json_data, mock_isfile):
            output = self.shared_ip_obj.release_ips('10.0.0.3')
            self.assertNotIn('10.0.0.3', output)
            self.assertTrue(mock_load_json_data.called)
            self.assertTrue(mock_isfile.called)

    def test_get_all_vms(self):
        fake_vm = ['vm1', 'vm2']
        with contextlib.nested(
            patch.object(util.VMwareUtils, 'get_view_ref', return_value=None),
            patch.object(util.VMwareUtils, 'collect_properties',
                         return_value=fake_vm)) as (
                mock_get_view_ref, mock_collect_properties):
            output = self.vmware_util.get_all_vms(MOB.content, None)
            self.assertEqual(fake_vm, output)
            self.assertTrue(mock_get_view_ref.called)
            self.assertTrue(mock_collect_properties.called)

    def test_get_all_hosts(self):
        container = {'obj': 'cluster-obj'}
        fake_host = ['host1', 'host2']
        with contextlib.nested(
            patch.object(util.VMwareUtils, 'get_view_ref', return_value=None),
            patch.object(util.VMwareUtils, 'collect_properties',
                         return_value=fake_host)) as (
                mock_get_view_ref, mock_collect_properties):
            output = self.vmware_util.get_all_hosts(MOB.content, container)
            self.assertEqual(fake_host, output)
            self.assertTrue(mock_get_view_ref.called)
            self.assertTrue(mock_collect_properties.called)

    def test_get_data_center(self):
        fake_dc = [{'name': 'DC-1'}, {'name': 'DC-2'}]
        with contextlib.nested(
            patch.object(util.VMwareUtils, 'get_view_ref', return_value=None),
            patch.object(util.VMwareUtils, 'collect_properties',
                         return_value=fake_dc)) as (
                mock_get_view_ref, mock_collect_properties):
            output = self.vmware_util.get_data_center(MOB.content, 'DC-1')
            self.assertEqual(fake_dc[0], output)
            self.assertTrue(mock_get_view_ref.called)
            self.assertTrue(mock_collect_properties.called)

    def test_get_cluster(self):
        fake_cluster = [{'mo_id': 'cluster-012'}, {'mo_id': 'cluster-013'}]
        with contextlib.nested(
            patch.object(util.VMwareUtils, 'get_view_ref',
                         return_value=None),
            patch.object(util.VMwareUtils, 'collect_properties',
                         return_value=fake_cluster)) as (
                mock_get_view_ref, mock_collect_properties):
            output = self.vmware_util.get_cluster(MOB.content,
                                                  None, 'cluster-012')
            self.assertEqual(fake_cluster[0], output)
            self.assertTrue(mock_get_view_ref.called)
            self.assertTrue(mock_collect_properties.called)

    def _valid_datastore(self, mountInfo=True):
        class DatastoreHost:
            key = host

            class mountInfo:
                mounted = True

        class VaildDataStore(DataStore):
            host = [DatastoreHost]

        DatastoreHost.mountInfo.mounted = mountInfo
        VaildDataStore.summary.accessible = True
        VaildDataStore.summary.maintenanceMode = 'normal'
        if mountInfo:
            with patch.object(util.VMwareUtils,
                              '_get_max_capacity_datastore') as (
                    mock_get_max_capacity_datastore):
                output = self.vmware_util._validate_datastore([VaildDataStore],
                                                              [host])
                self.assertTrue(mock_get_max_capacity_datastore.called)
                return output
        else:
            return self.vmware_util._validate_datastore([VaildDataStore],
                                                        [host])

    def test_valid_datastore(self):
            output = self._valid_datastore()
            self.assertTrue(output)

    def test_invalid_umounted_datastore(self):
        output = self._valid_datastore(False)
        self.assertIsNone(output)

    def test_invalid_datastore(self):
        DataStore.summary.accessible = False
        output = self.vmware_util._validate_datastore([DataStore], [host])
        self.assertIsNone(output)

    def test_max_capacity_datastore(self):
        class MaxCapacityDatastore1(DataStore):
            class summary:
                freeSpace = _gb2byte(900)

        class MaxCapacityDatastore2(DataStore):
            class summary:
                freeSpace = _gb2byte(1000)

        class MaxCapacityDatastore3(DataStore):
            class summary:
                freeSpace = _gb2byte(800)

        output = self.vmware_util._get_max_capacity_datastore(
            [MaxCapacityDatastore1, MaxCapacityDatastore2,
             MaxCapacityDatastore3])
        self.assertEqual(MaxCapacityDatastore2, output)

    def test_get_shared_datastore(self):
        fake_host = {'cluster': {
            'obj': 'cluster-obj',
            'host': [host]
        },
            'datastore': [DataStore],
            'obj': host}
        with contextlib.nested(
            patch.object(util.VMwareUtils, '_validate_datastore',
                         return_value=[]),
            patch.object(util.VMwareUtils, '_is_single_active_host',
                         return_value=True),
            patch.object(util.VMwareUtils, '_get_single_host_shared_storage',
                         return_value=[])) as (
                mock_validate_ds, mock_is_single_active_host,
                mock_get_single_host_shared_storage):
            output = self.vmware_util.get_shared_datastore(fake_host, None)
            self.assertEqual([], output)
            self.assertFalse(mock_validate_ds.called)
            self.assertTrue(mock_is_single_active_host.called)
            self.assertTrue(mock_get_single_host_shared_storage.called)

    def test_get_pcipt_spec(self):
        with patch.object(util.VMwareUtils, '_get_virtual_device_spec',
                          return_value=PCI) as mock_get_virtual_device_spec:
            pcispec = self.vmware_util.get_pcipt_spec([PCI], '04:00.0')
            self.assertEqual(pcispec.device.backing.id, PCI.pciDevice.id)
            self.assertEqual(pcispec.device.backing.systemId, PCI.systemId)
            self.assertEqual(pcispec.device.backing.vendorId,
                             PCI.pciDevice.vendorId)
            self.assertTrue(mock_get_virtual_device_spec.called)

    def test_get_net_mask(self):
        output = self.shared_ip_obj.get_net_mask('10.0.0.0/24')
        self.assertEqual('255.255.255.0', output)

    def test_store_ips(self):
        with contextlib.nested(
                patch.object(util, 'update_json_data'),
                patch.object(util, 'dump_json_data')) as (
                    mock_update_json_data, mock_dump_json_data):
            self.shared_ip_obj._store_ips(['10.0.0.1', '10.0.0.2'])
            self.assertTrue(mock_update_json_data.called)
            self.assertTrue(mock_dump_json_data.called)

    def test_wait_for_vmware_tools(self):
        self.assertIsNone(
            self.vmware_util.wait_for_vmware_tools(VM, 'host'))

    def test_get_view_ref(self):
        obj = self.vmware_util.get_view_ref(MOB.content,
                                            'obj_type', 'vim_type')
        self.assertIsInstance(obj, MOB.content.viewManager.CreateContainerView)

    def test_collect_properties(self):
        pass

    def test_get_vm(self):
        session = {'content': MOB.content}
        all_vm_refs = [{'name': 'vm_name'}]
        with patch.object(util.VMwareUtils, 'get_all_vms',
                          return_value=all_vm_refs) as mock_get_all_vms:
            output = self.vmware_util.get_vm(session, 'vm_name', None)
            self.assertEqual(all_vm_refs[0], output)
            self.assertTrue(mock_get_all_vms.called)

    def test_get_template(self):
        with patch.object(util.VMwareUtils, 'get_vm',
                          return_value='fake-template') as mock_get_vm:
            output = self.vmware_util.get_template('session', 'vm_name')
            self.assertEqual('fake-template', output)
            self.assertTrue(mock_get_vm.called)

    def test_get_template_with_none(self):
        with patch.object(util.VMwareUtils, 'get_vm',
                          return_value=None) as mock_get_vm:
            output = self.vmware_util.get_template('session', 'vm_name')
            self.assertIsNone(output)
            self.assertTrue(mock_get_vm.called)

    def test_validate_datastore(self):
        pass

    def test_get_cluster_shared_storage(self):
        pass

    def test_get_single_host_shared_storage(self):
        pass

    def test_is_single_active_host(self):
        pass

    def test_get_virtual_device_spec(self):
        pass

    def test_get_vnic_spec(self):
        pass

    def test_get_vmxnet3_spec(self):
        pass

    def test_get_sriov_spec(self):
        pass

    def test_get_virtual_devices(self):
        pass

    def test_get_vm_config(self):
        pass

    def test_get_relocation_spec(self):
        pass

    def test_clone_vm(self):
        pass

    def test_get_command_path(self):
        pass

    def test_exec_command_in_guest(self):
        pass

    def test_send_file_in_guest(self):
        pass

    def test_send_ssh_key(self):
        pass

    def test_send_prep_script(self):
        pass

    def test_customize_service_vm(self):
        pass

    def test_get_vmconfig_input(self):
        trunk_pg = {'vlan': '1-4094', 'switchName': 'TRUNK-DVS',
                    'name': 'TRUNK', 'vlan_type': 'trunk'}
        with patch.object(util, 'get_trunk_dvs_pg',
                          return_value=['', trunk_pg]) as (
                mock_get_trunk_dvs_pg):
            output = util.get_vmconfig_input(fake_inputs.data, 'OVSVAPP')
            self.assertEqual('OVSVAPP-ROLE', output['server_role'])
            self.assertTrue(mock_get_trunk_dvs_pg.called)

    def test_get_conf_pg(self):
        fake_validate = {'vlan_type': 'trunk',
                         'name': 'ESX-CONF',
                         'vlan': '33',
                         'switchName': 'MGMT-DVS',
                         'device': 'device1',
                         'nic_teaming': {
                             'network_failover_detection': '1',
                             'active_nics': 'vmnic1',
                             'load_balancing': '1',
                             'notify_switches': 'yes'}
                         }
        vm_config = {'nics': [{'portGroup': 'ESX-CONF', 'device': 'device1'}]}
        output = util.get_conf_pg(fake_inputs.data, vm_config)
        self.assertEqual(fake_validate, output)

    def test_get_conf_network_details(self):
        conf_ip, conf_mac = util.VMwareUtils.get_conf_network_details(
            VM, 'ESX-Conf')
        self.assertEqual('10.10.10.40', conf_ip)
        self.assertEqual('aa:bb:cc:dd:ee:fh', conf_mac)

    def test_get_trunk_dvs_pg(self):
        trunk_dvs = {'type': 'dvSwitch', 'name': 'TRUNK-DVS',
                     'physical_nics': '', 'mtu': '1500'}
        trunk_pg = {'vlan': '1-4094', 'switchName': 'TRUNK-DVS',
                    'name': 'TRUNK', 'vlan_type': 'trunk'}
        output = util.get_trunk_dvs_pg(fake_inputs.data)
        self.assertEqual(trunk_dvs, output[0])
        self.assertEqual(trunk_pg, output[1])

    def test_reserve_guest_memory(self):
        self.assertTrue(util.reserve_guest_memory([{'type': 'pcipt'}]))
        self.assertIsNone(util.reserve_guest_memory([{'type': 'sriov'}]))

    def test_find_by(self):
        pass

    def test_find_by_name(self):
        entity_type = vim.DistributedVirtualSwitch
        with contextlib.nested(
                patch.object(vim.DistributedVirtualSwitch, '__init__',
                             return_value=None),
                patch.object(util, 'find_by')) as (
                    mock_dvs, mock_find_by):
            name = 'dvs1'
            util.find_by.return_value = [vim.DistributedVirtualSwitch()]
            output = util.find_by_name(PrepFolder(), name, entity_type)
            self.assertTrue(output)
            self.assertTrue(mock_dvs.called)
            self.assertTrue(mock_find_by.called)

    def test_invalid_find_by_name(self):
            entity_type = vim.dvs.DistributedVirtualPortgroup
            with contextlib.nested(
                    patch.object(vim.DistributedVirtualSwitch, '__init__',
                                 return_value=None),
                    patch.object(util, 'find_by')) as (
                        mock_dvs, mock_find_by):
                name = 'dvs1'
                util.find_by.return_value = [vim.DistributedVirtualSwitch()]
                output = util.find_by_name(PrepFolder(), name, entity_type)
                self.assertIsNone(output)
                self.assertTrue(mock_dvs.called)
                self.assertTrue(mock_find_by.called)

    def test_find_by_name_without_entity_type(self):
            with contextlib.nested(
                    patch.object(vim.VirtualMachine, '__init__',
                                 return_value=None),
                    patch.object(util, 'find_by')) as (
                        mock_vm, mock_find_by):
                name = 'dvs1'
                util.find_by.return_value = [vim.VirtualMachine()]
                output = util.find_by_name(PrepFolder(), name)
                self.assertTrue(output)
                self.assertTrue(mock_vm.called)
                self.assertTrue(mock_find_by.called)

    def test_is_valid_ipv4(self):
        self.assertTrue(util.is_valid_ipv4('10.0.0.1'))
        self.assertFalse(util.is_valid_ipv4('10.0.0.'))

    def test_load_json_data(self):
        pass

    def test_update_json_data(self):
        pass

    def test_dump_json_data(self):
        pass

    def test_read_file(self):
        pass

    def test_str2bool(self):
        self.assertTrue(util.str2bool("yes"))
        self.assertTrue(util.str2bool("true"))
        self.assertTrue(util.str2bool("t"))
        self.assertTrue(util.str2bool("1"))
        self.assertFalse(util.str2bool("false"))
        self.assertFalse(util.str2bool("no"))

    def test_str2list(self):
        output = util.str2list("1,Two,iii")
        self.assertEqual(['1', 'Two', 'iii'], output)
