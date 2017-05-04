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

import mock
from mock import call
from eon.virt.rhel import validator
from eon.tests.unit import base_test
from eon.common import exception
from eon.virt import constants as kvm_constants


class TestRhelDriver(base_test.TestCase):

    def setUp(self):
        super(TestRhelDriver, self).setUp()
        self.resource_inventory = {"ip_address": "0.0.0.0",
                                   "username": "stack", "password": "password"}
        self.rhel_validator = validator.RHELValidator(self.resource_inventory)
        self.username = self.resource_inventory["username"]
        self.hostname = self.resource_inventory["ip_address"]

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.get')
    def test__verify_subscription_yum_repo_disabled_ssh_exception(self,
                                                                  mockGet):
        mockGet.side_effect = [Exception]
        self.assertRaises(
            exception.PreActivationCheckError,
            self.rhel_validator._verify_subscription_yum_repo_disabled)
        self.assertEquals(mockGet.call_count, 1)
        mockGet.assert_called_with(kvm_constants.SUBSCRIPTION_REPO_PATH)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.get')
    def test__verify_subscription_yum_repo_disabled(self, mockGet):
        """
        [main]
        enabled=0
        """
        lines = ["[main]\n", "enabled=0"]
        file = "subscription-manager.conf"
        with open(file, "w") as fw:
            fw.writelines(lines)

        mockGet.return_value = file
        self.rhel_validator._verify_subscription_yum_repo_disabled()
        mockGet.assert_called_once_with(kvm_constants.SUBSCRIPTION_REPO_PATH)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.get')
    def test__verify_subscription_yum_repo_not_disabled(self, mockGet):
        """
        [main]
        enabled=1
        """
        lines = ["[main]\n", "enabled=1"]
        file = "subscription-manager.conf"
        with open(file, "w") as fw:
            fw.writelines(lines)

        mockGet.return_value = file
        self.assertRaises(exception.PreActivationCheckError,
                self.rhel_validator._verify_subscription_yum_repo_disabled)
        mockGet.assert_called_once_with(kvm_constants.SUBSCRIPTION_REPO_PATH)

    @mock.patch(
        'eon.common.ssh_utilities.RemoteConnection.exec_command_and_wait')
    def test_check_computenode_kernel_version(self, mockExec):
        mockExec.return_value = (0, "3.10.0-327.el7.x86_64", "")
        self.rhel_validator._check_compute_node_kernel_version()
        mockExec.assert_called_once_with(kvm_constants.CHECK_KERNAL_VERSION,
                                         raise_on_exit_not_0=True)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
           'exec_command_and_wait')
    def test_check_computenode_kernel_version_exception(self, mockExec):
        mockExec.return_value = (1, "", "")
        mockExec.side_effect = [exception.PreActivationCheckError]
        self.assertRaises(
            exception.PreActivationCheckError,
            self.rhel_validator._check_compute_node_kernel_version)
        mockExec.assert_called_once_with(kvm_constants.CHECK_KERNAL_VERSION,
                                         raise_on_exit_not_0=True)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
           'exec_command_and_wait')
    def test_check_computenode_kernel_version_unsupported(self, mockExec):
        mockExec.return_value = (0, "#UnsupportedVersion#", "")
        mockExec.side_effect = [exception.PreActivationCheckError]
        self.assertRaises(
            exception.PreActivationCheckError,
            self.rhel_validator._check_compute_node_kernel_version)
        mockExec.assert_called_once_with(kvm_constants.CHECK_KERNAL_VERSION,
                                         raise_on_exit_not_0=True)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
           'exec_command_and_wait')
    def test_check_computenode_kernel_version_cmd_exception(self, mockExec):
        mockExec.return_value = (1, "", "")
        rh_ex = exception.RhelCommandNoneZeroException(
            'exitcode = 1 STDOUT: null STDERR: error')
        mockExec.side_effect = [rh_ex]
        self.assertRaises(
            exception.PreActivationCheckError,
            self.rhel_validator._check_compute_node_kernel_version)
        mockExec.assert_called_once_with(kvm_constants.CHECK_KERNAL_VERSION,
                                         raise_on_exit_not_0=True)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
           'exec_command_and_wait')
    def test_check_virsh_empty_instance(self, mockExec):
        std_out = 'id  Name   State\n------------------\n\n'
        calls = [call('virsh list --all')]
        mockExec.side_effect = [(0, "", ""), (0, std_out, "")]
        self.rhel_validator.check_instances()
        mockExec.assert_has_calls(calls)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
           'exec_command_and_wait')
    def test_check_virsh_empty_instance_with_VM(self, mockExec):
        std_out = 'id  Name   State\n------------------\n 123   aVM  running\n'
        mockExec.side_effect = [(0, std_out, ""), (0, std_out, "")]
        self.rhel_validator.check_instances()

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
           'exec_command_and_wait')
    def test_check_failed_virsh(self, mockExec):
        calls = [call('virsh list --all')]
        mockExec.side_effect = [Exception]
        self.rhel_validator.check_instances()
        mockExec.assert_has_calls(calls)
