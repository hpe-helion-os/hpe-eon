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

import eon.common.log as logging
from eon.deployer import util, upload_ova
from eon.deployer.network.ovsvapp.install.create_ovs_vapp_vm import (
    OVSvAppFactory)
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.tests.unit.deployer import fake_inputs
from eon.tests.unit import tests

LOG = logging.getLogger(
    'eon.deployer.network.ovsvapp.install.create_ovs_vapp_vm')


class vm:
    name = 'vm1'

    class guest:
        ipAddress = '10.10.10.10'

        class Nic:
            network = 'conf-pg'
            macAddress = "ff:ff:ff:ff:ff"

        net = [Nic]


class TestOVSvAppFactoryVm(tests.BaseTestCase):

    def setUp(self):
        super(TestOVSvAppFactoryVm, self).setUp()
        self.create_ovs_vapp = OVSvAppFactory(fake_inputs.data)

    def test_construct_error_json(self):
        fake_result_validate = {'status': 'failed', 'host-moid': 'mo-123',
                                'status_msg': 'fake_error',
                                'esx_hostname': 'host-1',
                                'conf_ip': '10.10.10.10'}
        output = self.create_ovs_vapp._error_json(
            name='host-1', mo_id='mo-123',
            status_msg='fake_error', conf_ip='10.10.10.10')
        self.assertEqual(fake_result_validate, output)

    def test_get_ovsvapp_name(self):
        with patch.object(util, 'is_valid_ipv4') as mock_is_valid_ipv4:
            self.assertEqual('ovsvapp-10-10-10-10',
                             self.create_ovs_vapp._get_ovsvapp_name(
                                 '10.10.10.10'))
            self.assertTrue(mock_is_valid_ipv4.called)

        self.assertEqual('ovsvapp-fake.vmware.address',
                         self.create_ovs_vapp._get_ovsvapp_name(
                             'fake.vmware.address'))

    def test_get_ovsvapp_vm_details(self):
        host = {'name': 'host-1', 'mo_id': 'mo-123'}
        with patch.object(util.VMwareUtils, 'get_conf_ip_and_mac',
                          return_value=['10.10.10.2', 'ff:ff:ff:ff:ff']):
            output = self.create_ovs_vapp._get_ovsvapp_vm_details(
                vm, host, 'conf-pg', 'role', '10.10.10.2')
            self.assertEqual('success', output['status']),
            self.assertEqual('mo-123', output['host-moid'])
            self.assertEqual('ff:ff:ff:ff:ff', output['pxe-mac-addr'])
            self.assertEqual('host-1', output['esx_hostname'])
            self.assertEqual('role', output['server_role'])
            self.assertEqual('10.10.10.2', output['pxe-ip-addr'])

    def test_create_vm(self):
        with patch.object(vim.VirtualMachine, '__init__',
                          return_value=None) as mock_constructor:
            self.vm_obj = vim.VirtualMachine()
            self.assertTrue(mock_constructor.called)

        fake_vm_config = {'nics': ['nic1'],
                          'template_name': 'fake-template_name',
                          'template_location': 'template_loc',
                          'server_role': 'fake-server_role'}
        host = {'name': 'fake-name', 'cluster': fake_inputs.fake_clusters,
                'mo_id': 'fake-mo_id', 'obj': 'fake-obj',
                'shared_storage': 'fake-shared_storage'}
        with contextlib.nested(
            patch.object(util.VMwareUtils, 'get_virtual_devices',
                         return_value=fake_vm_config),
            patch.object(util.VMwareUtils, 'get_vm_config'),
            patch.object(util.VMwareUtils, 'get_relocation_spec'),
            patch.object(upload_ova.OVAUploadManager, 'upload_ova'),
            patch.object(OVSvAppFactory, '_get_ovsvapp_name'),
            patch.object(util.VMwareUtils, 'clone_vm',
                         return_value=self.vm_obj),
            patch.object(OVSvAppUtil, 'disable_ha_on_ovsvapp'),
            patch.object(util.ServiceVMCustomizer, 'customize_service_vm'),
            patch.object(OVSvAppFactory, '_get_ovsvapp_vm_details',
                         return_value={})) as (
                mock_get_virtual_devices, mock_get_vm_config,
                mock_get_relocation_spec, mock_get_template,
                mock_get_ovsvapp_name, mock_clone_vm,
                mock_disable_ha_on_ovsvapp, mock_customize_service_vm,
                mock_get_ovsvapp_vm_details):
            output = self.create_ovs_vapp.create_vm(
                fake_inputs.session,
                fake_inputs.fake_datacenter,
                host, False, '10.10.10.2')
            self.assertEqual({}, output)
            self.assertTrue(mock_get_virtual_devices.called)
            self.assertTrue(mock_get_vm_config.called)
            self.assertTrue(mock_get_relocation_spec.called)
            self.assertTrue(mock_get_template.called)
            self.assertTrue(mock_get_ovsvapp_name.called)
            self.assertTrue(mock_clone_vm.called)
            self.assertTrue(mock_disable_ha_on_ovsvapp.called)
            self.assertTrue(mock_customize_service_vm.called)
            self.assertTrue(mock_get_ovsvapp_vm_details.called)

    def test_create_vm_failure(self):
        fake_vm_config = {'nics': ['nic1'],
                          'template_name': 'fake-template_name',
                          'template_location': 'fake_location',
                          'server_role': 'fake-server_role'}
        host = {'name': 'fake-name', 'cluster': fake_inputs.fake_clusters,
                'mo_id': 'fake-mo_id', 'obj': 'fake-obj',
                'shared_storage': 'fake-shared_storage'}
        with contextlib.nested(
            patch.object(util.VMwareUtils, 'get_virtual_devices',
                         return_value=fake_vm_config),
            patch.object(util.VMwareUtils, 'get_vm_config'),
            patch.object(util.VMwareUtils, 'get_relocation_spec'),
            patch.object(upload_ova.OVAUploadManager, 'upload_ova'),
            patch.object(OVSvAppFactory, '_get_ovsvapp_name'),
            patch.object(util.VMwareUtils, 'clone_vm',
                         return_value=None),
            patch.object(OVSvAppFactory, '_error_json',
                         return_value={}),
            patch.object(LOG, 'error')) as (
                mock_get_virtual_devices, mock_get_vm_config,
                mock_get_relocation_spec,
                mock_upload_ova,
                mock_get_ovsvapp_name, mock_clone_vm,
                mock_error_json, mock_log):
            output = self.create_ovs_vapp.create_vm(
                fake_inputs.session,
                fake_inputs.fake_datacenter,
                host, False, '10.10.10.2')
            self.assertEqual({}, output)
            self.assertTrue(mock_get_virtual_devices.called)
            self.assertTrue(mock_get_vm_config.called)
            self.assertTrue(mock_get_relocation_spec.called)
            self.assertTrue(mock_upload_ova.called)
            self.assertTrue(mock_get_ovsvapp_name.called)
            self.assertTrue(mock_clone_vm.called)
            self.assertTrue(mock_error_json.called)
            self.assertTrue(mock_log.called)

    def test_create_vm_exception(self):
        with patch.object(vim.VirtualMachine, '__init__',
                          return_value=None) as mock_constructor:
            self.vm_obj = vim.VirtualMachine()
            self.assertTrue(mock_constructor.called)

        fake_vm_config = {'nics': ['nic1'],
                          'template_name': 'fake-template_name',
                          'template_location': 'fake_location',
                          'server_role': 'fake-server_role'}
        host = {'name': 'fake-name', 'cluster': fake_inputs.fake_clusters,
                'mo_id': 'fake-mo_id', 'obj': 'fake-obj',
                'shared_storage': 'fake-shared_storage'}
        with contextlib.nested(
            patch.object(util.VMwareUtils, 'get_virtual_devices',
                         return_value=fake_vm_config),
            patch.object(util.VMwareUtils, 'get_vm_config'),
            patch.object(util.VMwareUtils, 'get_relocation_spec'),
            patch.object(upload_ova.OVAUploadManager, 'upload_ova'),
            patch.object(OVSvAppFactory, '_get_ovsvapp_name'),
            patch.object(util.VMwareUtils, 'clone_vm',
                         return_value=self.vm_obj),
            patch.object(OVSvAppUtil, 'disable_ha_on_ovsvapp'),
            patch.object(util.ServiceVMCustomizer, 'customize_service_vm'),
            patch.object(OVSvAppFactory, '_error_json',
                         return_value={}),
            patch.object(LOG, 'exception')) as (
                mock_get_virtual_devices, mock_get_vm_config,
                mock_get_relocation_spec, mock_upload_ova,
                mock_get_ovsvapp_name, mock_clone_vm,
                mock_disable_ha_on_ovsvapp, mock_customize_service_vm,
                mock_error_json, mock_log):
            self.create_ovs_vapp.create_vm(
                fake_inputs.session,
                fake_inputs.fake_datacenter,
                host, False, '10.10.10.2')
            self.assertTrue(mock_get_virtual_devices.called)
            self.assertTrue(mock_get_vm_config.called)
            self.assertTrue(mock_get_relocation_spec.called)
            self.assertTrue(mock_get_ovsvapp_name.called)
            self.assertTrue(mock_clone_vm.called)
            self.assertTrue(mock_upload_ova.called)
            self.assertTrue(mock_disable_ha_on_ovsvapp.called)
            self.assertTrue(mock_error_json.called)
            self.assertTrue(mock_log.called)
            self.assertTrue(mock_customize_service_vm.called)
