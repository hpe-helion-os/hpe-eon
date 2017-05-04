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

import copy
import mock
from mock import call
from eon.common import exception
from eon.virt.rhel import driver
from eon.tests.unit import fake_data
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.tests.unit import base_test
from eon.virt import constants
from eon.common.ssh_utilities import RemoteConnection


class TestRhelDriver(base_test.TestCase):

    def setUp(self):
        super(TestRhelDriver, self).setUp()
        self.rhel_driver = driver.RHELDriver()

    @mock.patch('eon.virt.rhel.validator.'
                'RHELValidator._verify_subscription_yum_repo_disabled')
    @mock.patch('eon.virt.rhel.validator.'
                'RHELValidator._check_compute_node_kernel_version')
    @mock.patch('eon.virt.rhel.validator.'
                'RHELValidator.check_instances')
    def test_pre_activation_steps(self, mock1, mock2, mock3):
        context = None
        resource_inventory = {"ip_address": "0.0.0.0",
                              "username": "stack", "password": "password"}
        self.rhel_driver.pre_activation_steps(context,
                                resource_inventory=resource_inventory)
        mock1.called_once_with()
        mock2.called_once_with()
        mock3.called_once_with()

    @mock.patch("eon.common.ssh_utilities.RemoteConnection."
                "exec_command_and_wait")
    def test_restart_ssh_post_activation(self, mocked_exec_ssh):
        calls = [call(constants.RESTART_SSH,
                      raise_on_exit_not_0=True)]
        resource_inventory = {"ip_address": "0.0.0.0",
                              "username": "stack", "password": "password"}
        remote_connection = RemoteConnection(
            resource_inventory.get("ip_address"),
            resource_inventory.get("username"),
            resource_inventory.get("password"))
        self.rhel_driver.restart_ssh_post_activation(remote_connection)
        mocked_exec_ssh.assert_has_calls(calls)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.'
                'HLMFacadeWrapper.run_playbook_by_ids')
    def test_run_wipe_disks(self, mocked_run_play):
        context = None
        hux_obj = HLMFacadeWrapper(context)
        resource_id = "78as8x8za122seeeeasdde"
        extra_args = {"extraVars": {
            "automate": "yes"
        }}
        self.rhel_driver.run_wipe_disks(hux_obj, resource_id)
        mocked_run_play.assert_called_once_with('wipe_disks', resource_id,
                                                extra_args=extra_args)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
                'exec_command_and_wait')
    @mock.patch('eon.virt.rhel.driver.RHELDriver.post_activation_steps')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_monitoring_playbooks')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook_by_ids')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_server_by_id')
    def test__invoke_activate_playbooks_run_playbook_skip_disk_config_true(
            self, m_update, m_commit, m_config_run, m_ready_dep, m_run_play,
            m_monitoring, m_post_activation, mock_rem_con):
        new_fake_data = copy.deepcopy(fake_data.network_prop)
        new_fake_data["skip_disk_config"] = True
        self.rhel_driver._invoke_activate_playbooks(self.context,
                           fake_data.fake_id1,
                           new_fake_data,
                           fake_data.resource_inventory,
                           run_playbook=True,
                           resource_inventory=fake_data.resource_inventory)
        m_update.assert_called_once_with(fake_data.resource_inventory,
                                         fake_data.fake_id1)
        m_commit.assert_called_once_with(
            fake_data.fake_id1,
            'Activate cobbler-provisioned KVM compute resource')
        m_config_run.assert_called_once_with()
        m_ready_dep.assert_called_once_with()
        m_run_play.assert_called_once_with('site',
                                           fake_data.fake_id1,
                                           extra_args=None)
        m_monitoring.assert_called_once_with()
        m_post_activation.assert_called_once_with(self.context,
                                              fake_data.fake_id1,
                                              fake_data.resource_inventory)
        calls = [call(constants.MKDIR_MARKER_PARENT_DIR,
                      raise_on_exit_not_0=True),
                 call(constants.CREATE_SKIP_DISK_CONFIG_MARKER,
                      raise_on_exit_not_0=True)]
        mock_rem_con.assert_has_calls(calls)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
                'exec_command_and_wait')
    @mock.patch('eon.virt.rhel.driver.RHELDriver.post_activation_steps')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_monitoring_playbooks')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook_by_ids')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_server_by_id')
    def test__invoke_activate_playbooks_run_playbook_skip_disk_config_false(
            self, m_update, m_commit, m_config_run, m_ready_dep, m_run_play,
            m_monitoring, m_post_activation, mock_rem_con):
        new_fake_data = copy.deepcopy(fake_data.network_prop)
        new_fake_data["skip_disk_config"] = False
        new_fake_data["run_wipe_disks"] = False
        self.rhel_driver._invoke_activate_playbooks(self.context,
                           fake_data.fake_id1,
                           new_fake_data,
                           fake_data.resource_inventory,
                           run_playbook=True,
                           resource_inventory=fake_data.resource_inventory)
        m_update.assert_called_once_with(fake_data.resource_inventory,
                                         fake_data.fake_id1)
        m_commit.assert_called_once_with(
            fake_data.fake_id1,
            'Activate cobbler-provisioned KVM compute resource')
        m_config_run.assert_called_once_with()
        m_ready_dep.assert_called_once_with()
        m_run_play.assert_called_once_with('site',
                                           fake_data.fake_id1,
                                           extra_args=None)
        m_monitoring.assert_called_once_with()
        m_post_activation.assert_called_once_with(self.context,
                                              fake_data.fake_id1,
                                              fake_data.resource_inventory)
        mock_rem_con.assert_called_once_with(
            constants.DELETE_SKIP_DISK_CONFIG_MARKER,
            raise_on_exit_not_0=True)

    @mock.patch("eon.common.ssh_utilities.RemoteConnection."
                "exec_command_and_wait")
    @mock.patch("eon.virt.common.utils.validate_nova_neutron_list")
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'model_generated_host_name')
    def test_post_activation_steps(self, mocked_host_name,
                                   mocked_utils, mocked_exec_ssh):
        context = {}
        resource_inventory = fake_data.kvm_resource_inventory
        mocked_host_name.return_value = "kvm_host_name"
        self.rhel_driver.post_activation_steps(context, "rhelcompute",
                                              resource_inventory)
        calls = [call(constants.DISABLE_PASSWD_AUTHENTICATION,
                      raise_on_exit_not_0=True),
                 call(constants.RESTART_SSH,
                      raise_on_exit_not_0=True)]
        mocked_exec_ssh.assert_has_calls(calls)

    @mock.patch("eon.common.ssh_utilities.RemoteConnection."
                "exec_command_and_wait")
    @mock.patch("eon.virt.common.utils.validate_nova_neutron_list")
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'model_generated_host_name')
    def test_post_activation_steps_exception(self, mocked_host_name,
                                   mocked_utils, mocked_exec_ssh):
        context = {}
        resource_inventory = fake_data.kvm_resource_inventory
        mocked_host_name.return_value = "kvm_host_name"
        mocked_exec_ssh.side_effect = [exception.RhelCommandNoneZeroException]
        self.assertRaises(exception.RhelCommandNoneZeroException,
                          self.rhel_driver.post_activation_steps,
                          context, "rhelcompute", resource_inventory)
        mocked_exec_ssh.assert_called_once_with(
            constants.DISABLE_PASSWD_AUTHENTICATION,
            raise_on_exit_not_0=True)
