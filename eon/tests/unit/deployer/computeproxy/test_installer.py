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

from eon.deployer import util
from eon.deployer.computeproxy import compute_proxy_vm
from eon.deployer.computeproxy.installer import ProxyInstaller
from eon.deployer.computeproxy import cp_utility
from eon.tests.unit import tests, fake_data
from eon.tests.unit.deployer.fake_inputs import data


class MOB:

    def __init__(self):
        pass

    def RetrieveContent(self):
        pass

    class content():

        def rootFolder(self):
            def find_by_name(self, vm_name):
                pass

        def propertyCollector(self):
            pass


class VM:

    class guest:
        ipAddress = '10.10.10.10'

    class runtime:
        powerState = 'poweredOn'

    name = 'fake_vm'


class TestProxyInstaller(tests.BaseTestCase):

    def setUp(self):
        super(TestProxyInstaller, self).setUp()
        self.proxyinstaller = ProxyInstaller()
        with patch.object(vim.VirtualMachine, '__init__', return_value=None):
            self.vim_instance = vim.VirtualMachine()

    def test_setup_network(self):
        with patch.object(cp_utility, "ProxyInstallerUtility") as (
                mock_proxy_utility):
            mock_create = (mock_proxy_utility.return_value.
                           create_network_infrastructure)
            self.proxyinstaller.setup_network(data)
            self.assertTrue(mock_create.called)

    def test_teardown_network(self):
        with patch.object(cp_utility, "ProxyInstallerUtility") as (
                mock_proxy_utility):
            mock_teardown = mock_proxy_utility.return_value.teardown_network
            self.proxyinstaller.teardown_network(data)
            self.assertTrue(mock_teardown.called)

    def test_create_if_vm_present(self):
        fake_proxy = dict()
        fake_vm = [{'name': 'novaproxy_DC-Fake_Cluster1'}]
        with contextlib.nested(
            patch.object(cp_utility, "ProxyInstallerUtility"),
            patch.object(util.VMwareUtils, "get_vcenter_session",
                         return_value=MOB()),
            patch.object(compute_proxy_vm, 'get_vm_location_details'),
            patch.object(util.VMwareUtils, 'get_all_vms',
                         return_value=fake_vm)) as (
                mock_proxy_utility,
                mock_get_vcenter_session, mock_vm_location,
                mock_get_all_vms):
            proxy_info = self.proxyinstaller.create(data)
            self.assertTrue(mock_get_vcenter_session.called)
            self.assertEqual(fake_proxy, proxy_info)
            self.assertTrue(mock_vm_location.called)
            self.assertTrue(mock_get_all_vms)

    def test_create(self):
        fake_result = {'name': 'fake_name',
                       'pxe-ip-addr': '127.0.0.1',
                       'pxe-mac-addr': 'ff:ff:ff'}
        fake_template = {'obj': 'vcenter-fake-template'}
        with contextlib.nested(
            patch.object(cp_utility, "ProxyInstallerUtility"),
            patch.object(util.VMwareUtils, "get_vcenter_session",
                         return_value=MOB()),
            patch.object(compute_proxy_vm, 'get_vm_location_details'),
            patch.object(util.VMwareUtils, 'get_virtual_devices'),
            patch.object(util.VMwareUtils, 'get_relocation_spec'),
            patch.object(util.VMwareUtils, 'clone_vm',
                         return_value=self.vim_instance),
            patch.object(util.ServiceVMCustomizer, 'customize_service_vm'),
            patch.object(util.VMwareUtils, 'get_vm',
                         return_value=None),
            patch.object(util.VMwareUtils, 'get_template',
                         return_value=fake_template),
            patch.object(util.SharedIPAllocator, 'get_ips',
                         return_value=['10.0.0.2', '10.0.0.3']),
            patch.object(compute_proxy_vm, 'get_shell_vm_info',
                         return_value=fake_result)) as (
                mock_proxy_utility,
                mock_get_vcenter_session, mock_get_vm_location_details,
                mock_get_virtual_devices, mock_reloc_spec, mock_clone_vm,
                mock_customize_service_vm, mock_get_all_vms,
                mock_get_template, mock_get_ips, mock_get_shell_vm_info):
            proxy_info = self.proxyinstaller.create(data)
            self.assertEqual(fake_result, proxy_info)
            self.assertTrue(mock_get_vcenter_session.called)
            self.assertTrue(mock_get_vm_location_details.called)
            self.assertTrue(mock_get_virtual_devices.called)
            self.assertTrue(mock_reloc_spec.called)
            self.assertTrue(mock_clone_vm.called)
            self.assertTrue(mock_customize_service_vm.called)
            self.assertTrue(mock_get_all_vms.called)
            self.assertTrue(mock_get_template.called)
            self.assertTrue(mock_get_ips.called)
            self.assertTrue(mock_get_shell_vm_info.called)

    def test_update(self):
        pass

    def test_delete(self):
        with contextlib.nested(
            patch.object(ProxyInstaller, '_get_session'),
            patch.object(ProxyInstaller, '_get_proxy_vm_name'),
            patch.object(ProxyInstaller, '_get_conf_pg_name'),
            patch.object(compute_proxy_vm, 'delete_shell_vm')) as (
                mock_get_session, mock_get_proxy_vm_name,
                mock_get_conf_pg_name, mock_delete_shell_vm):
            self.proxyinstaller.delete(data)
            self.assertTrue(mock_get_session.called)
            self.assertTrue(mock_get_proxy_vm_name.called)
            self.assertTrue(mock_get_conf_pg_name.called)
            self.assertTrue(mock_delete_shell_vm.called)

    def test_get_info(self):
        pass

    def test_get_session(self):
        with patch.object(util.VMwareUtils, 'get_vcenter_session',
                          return_value=MOB()) as (
                mock_get_vcenter_session):
            self.proxyinstaller._get_session(data)
            self.assertTrue(mock_get_vcenter_session.called)

    def test_get_proxy_vm_name(self):
        output = self.proxyinstaller._get_proxy_vm_name(data)
        self.assertEqual('novaproxy_DC-Fake_Cluster1', output)

    def test_delete_template(self):
        session = fake_data.FakeVCSession()
        with contextlib.nested(
            patch.object(self.proxyinstaller, "_get_session",
                        return_value=session),
            patch.object(self.proxyinstaller, "_get_template_name",
                         return_value="hlm-shell-ova"),
            patch.object(compute_proxy_vm, "delete_vm"),
                               ) as (
                        mock_session, mock_get_temp, delete_vm):
            self.proxyinstaller.delete_template(data)
            mock_session.assert_called_once_with(data)
            mock_get_temp.assert_called_once_with(data)
            delete_vm.assert_called()

    def test_delete_template_no_template(self):
        session = fake_data.FakeVCSession()
        with contextlib.nested(
            patch.object(self.proxyinstaller, "_get_session",
                        return_value=session),
            patch.object(self.proxyinstaller, "_get_template_name",
                         return_value="hlm-shell-ova123"),
            patch.object(compute_proxy_vm, "delete_vm"),
                               ) as (
                        mock_session, mock_get_temp, delete_vm):
            self.proxyinstaller.delete_template(data)
            mock_session.assert_called_once_with(data)
            mock_get_temp.assert_called_once_with(data)
            delete_vm.assert_not_called()
