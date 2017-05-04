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
from eon.hlm_facade import exception as facade_excep
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.virt.kvm import driver
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
from eon.virt import constants


class Prop(object):
    """Property Object base class."""

    def __init__(self):
        self.name = None
        self.value = None


class TestDriver(base_test.TestCase):

    def setUp(self):
        super(TestDriver, self).setUp()
        self.kvm_driver = driver.KVMDriver()
        self.comp_mock_driver = mock.MagicMock()
        self.net_mock_driver = mock.MagicMock()

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.close_connection')
    @mock.patch('eon.common.ssh_utilities.RemoteConnection.open_connection')
    def test_validate_create(self, mock_oc, mock_cc):
        context = {}
        data = self.kvm_driver.validate_create(context, fake_data.create_data)
        self.assertEquals(fake_data.create_data, data,
                          "Invalid values returned")
        mock_oc.called_once_with()
        mock_cc.called_once_with()

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.close_connection')
    @mock.patch('eon.common.ssh_utilities.RemoteConnection.open_connection')
    def test_validate_create_excep1(self, mock_oc, mock_cc):
        mock_oc.side_effect = Exception
        context = {}
        self.assertRaises(exception.CreateException,
                          self.kvm_driver.validate_create,
                          context, fake_data.create_data)
        mock_oc.called_once_with()
        mock_cc.called_once_with()

    def test_validate_delete(self):
        fake_data.res_mgr_data1["state"] = "provisioned"
        self.assertIsNone(self.kvm_driver.validate_delete(
            fake_data.res_mgr_data1))

    def test_validate_delete_exception(self):
        fake_data.res_mgr_data1["state"] = "importing"
        self.assertRaises(exception.EonException,
                          self.kvm_driver.validate_delete,
                          fake_data.res_mgr_data1)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_monitoring_playbooks')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook_by_ids')
    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_server_by_id')
    @mock.patch('eon.virt.kvm.driver.KVMDriver._build_input_model_data')
    @mock.patch('eon.virt.kvm.driver.KVMDriver.post_activation_steps')
    @mock.patch('eon.openstack.common.lockutils.synchronized')
    def test_activate(self, m_lock, m_post, m_build, m_up_id,
                      m_commit, m_update, m_r_p,
                      m_c_r, m_r_d, m_r_m_p):
        self.kvm_driver.activate(self.context,
                            fake_data.fake_id1,
                            fake_data.network_prop,
                            resource_inventory=fake_data.resource_inventory,
                            run_playbook=True)
        self.assertEquals(1, m_post.call_count)
        self.assertEquals(1, m_build.call_count)
        self.assertEquals(1, m_up_id.call_count)
        self.assertEquals(1, m_commit.call_count)
        self.assertEquals(2, m_update.call_count)
        self.assertEquals(1, m_r_p.call_count)
        self.assertEquals(1, m_c_r.call_count)
        self.assertEquals(1, m_r_d.call_count)
        self.assertEquals(1, m_r_m_p.call_count)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'model_generated_host_name')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'delete_server')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'revert_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook_by_ids')
    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    @mock.patch('eon.openstack.common.lockutils.synchronized')
    def test_deactivate(self, m_lock, m_update, m_run_play,
                        m_r_v, mrd, mcpr, mcc, mds, hname):
        hname.return_value = "hypervisor_hostname"
        self.kvm_driver.deactivate(self.context,
                            fake_data.fake_id1,
                            resource_inventory=fake_data.resource_inventory,
                            run_playbook=True)
        calls = [call('hlm_stop', fake_data.fake_id1),
                 call('hlm_post_deactivation', fake_data.fake_id1)]
        m_run_play.assert_has_calls(calls)
        self.assertEquals(1, mrd.call_count)
        self.assertEquals(1, mcpr.call_count)
        self.assertEquals(1, mcc.call_count)
        self.assertEquals(1, mds.call_count)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook')
    def test_delete(self, mocked_playbook):
        uuid_node = "asdsdai112877sasddasds9888978sadasdasdasd"
        self.kvm_driver.delete(self.context, uuid_node)
        extra_args = {"extraVars": {
            "nodename": uuid_node
        }}
        mocked_playbook.assert_called_once_with('hlm_remove_cobbler_node',
                                                extra_args=extra_args)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook_by_ids')
    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'delete_server')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'revert_changes')
    def test_rollback_activate(self, mock_rev, mock_update,
                               mock_commit, mock_prop, m_r_p, m_c_p, m_r_d):
        hux_obj = HLMFacadeWrapper(self.context)
        self.kvm_driver._rollback_activate(self.context, hux_obj,
                                              fake_data.res_data,
                                              True)
        mock_commit.assert_called_once_with(
            fake_data.res_data['id'],
            "Deactivate/Rollback KVM compute resource")
        mock_rev.assert_called_once_with()

    @mock.patch("eon.virt.common.utils.check_for_running_vms")
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'model_generated_host_name')
    def test_pre_deactivation_steps(self, mocked_host_name, mocked_utils):
        context = {}
        resource_inventory = {"id": "rhelcompute",
                              "ip_address": "12.12.12.69",
                              "username": "stack",
                              "password": "password",
                              "EON_RESOURCE_NAME": "rhel"}
        mocked_host_name.return_value = "kvm_host_name"
        self.kvm_driver.pre_deactivation_steps(context,
                                        resource_inventory=resource_inventory)
        mocked_host_name.assert_called_once_with("rhelcompute")
        mocked_utils.assert_called_once_with(self.kvm_driver, context,
                         "kvm_host_name", resource_inventory)

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
        self.kvm_driver.post_activation_steps(context, "rhelcompute",
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
                          self.kvm_driver.post_activation_steps,
                          context, "rhelcompute", resource_inventory)
        mocked_exec_ssh.assert_called_once_with(
            constants.DISABLE_PASSWD_AUTHENTICATION,
            raise_on_exit_not_0=True)

    @mock.patch('eon.virt.kvm.driver.KVMDriver._rollback_activate')
    def test__invoke_activate_playbooks_exception(self, mocked_rollback):
        self.assertRaises(Exception,
                          self.kvm_driver._invoke_activate_playbooks,
                          self.context, fake_data.fake_id1,
                          fake_data.network_prop,
                          fake_data.resource_inventory,
                          run_playbook=True,
                          resource_inventory=fake_data.resource_inventory)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_server_by_id')
    def test__invoke_activate_playbooks_dont_run_playbook(self, m_update):
        self.kvm_driver._invoke_activate_playbooks(self.context,
                           fake_data.fake_id1,
                           fake_data.network_prop,
                           fake_data.resource_inventory,
                           run_playbook=False,
                           resource_inventory=fake_data.resource_inventory)
        m_update.assert_called_once_with(fake_data.resource_inventory,
                                         fake_data.fake_id1)

    @mock.patch('eon.virt.kvm.driver.KVMDriver.post_activation_steps')
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
    def test__invoke_activate_playbooks_run_playbook(self,
                                 m_update, m_commit, m_config_run,
                                 m_ready_dep, m_run_play, m_monitoring,
                                 m_post_activation):
        self.kvm_driver._invoke_activate_playbooks(self.context,
                           fake_data.fake_id1,
                           fake_data.network_prop,
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
                                              fake_data.resource_inventory,
                                                  )

    @mock.patch('eon.virt.common.utils.check_if_os_config_ran')
    @mock.patch('eon.virt.kvm.driver.KVMDriver.run_wipe_disks')
    @mock.patch('eon.virt.kvm.driver.KVMDriver.post_activation_steps')
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
    def test__invoke_activate_playbooks_run_playbook_wipe_disk(self,
                                 m_update, m_commit, m_config_run,
                                 m_ready_dep, m_run_play, m_monitoring,
                                 m_post_activation, m_run_wipe_disk,
                                 m_osconfig_ran):
        new_fake_data = copy.deepcopy(fake_data.network_prop)
        new_fake_data["skip_disk_config"] = False
        new_fake_data["run_wipe_disks"] = True
        m_osconfig_ran.return_value = False
        self.kvm_driver._invoke_activate_playbooks(self.context,
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
        self.assertEquals(m_run_wipe_disk.call_count, 1)

    @mock.patch('eon.virt.common.utils.check_if_os_config_ran')
    @mock.patch('eon.virt.kvm.driver.KVMDriver.post_activation_steps')
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
    def test__invoke_activate_playbooks_skip_playbook_wipe_disk(self,
                                 m_update, m_commit, m_config_run,
                                 m_ready_dep, m_run_play, m_monitoring,
                                 m_post_activation, m_osconfig_ran):
        new_fake_data = copy.deepcopy(fake_data.network_prop)
        new_fake_data["skip_disk_config"] = False
        new_fake_data["run_wipe_disks"] = True
        m_osconfig_ran.return_value = True
        self.kvm_driver._invoke_activate_playbooks(self.context,
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
        self.assertEquals(m_osconfig_ran.call_count, 1)

    @mock.patch('eon.virt.kvm.driver.KVMDriver.post_activation_steps')
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
            m_monitoring, m_post_activation):
        new_fake_data = copy.deepcopy(fake_data.network_prop)
        new_fake_data["skip_disk_config"] = True
        self.kvm_driver._invoke_activate_playbooks(self.context,
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

    @mock.patch('eon.virt.kvm.driver.KVMDriver.post_activation_steps')
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
            m_monitoring, m_post_activation):
        new_fake_data = copy.deepcopy(fake_data.network_prop)
        new_fake_data["skip_disk_config"] = False
        self.kvm_driver._invoke_activate_playbooks(self.context,
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

    @mock.patch('eon.virt.common.utils.get_encrypted_password')
    @mock.patch('eon.common.ssh_utilities.RemoteConnection.does_file_exist')
    @mock.patch('eon.virt.kvm.driver.KVMDriver.run_wipe_disks')
    @mock.patch('eon.virt.kvm.driver.KVMDriver.post_activation_steps')
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
                'create_server')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_server_by_id')
    def test__invoke_activate_playbooks_run_playbook_wipe_disk_except1(self,
                                 m_update, m_create_server, m_commit,
                                 m_config_run,
                                 m_ready_dep, m_run_play, m_monitoring,
                                 m_post_activation, m_run_wipe_disk,
                                 m_osconfig_ran, m_encrypt_pass):
        m_update.side_effect = [facade_excep.NotFound]
        new_fake_data = copy.deepcopy(fake_data.network_prop)
        new_fake_data["skip_disk_config"] = False
        new_fake_data["run_wipe_disks"] = True
        m_osconfig_ran.return_value = False
        self.kvm_driver._invoke_activate_playbooks(self.context,
                           fake_data.fake_id1,
                           new_fake_data,
                           fake_data.resource_inventory,
                           run_playbook=True,
                           resource_inventory=fake_data.resource_inventory)
        m_encrypt_pass.return_value = "encrypted-password"
        m_create_server.assert_called_once_with(fake_data.resource_inventory)
        m_commit.assert_called_once_with(
            fake_data.fake_id1,
            'Activate pre-provisioned KVM compute resource')
        m_config_run.assert_called_once_with()
        m_ready_dep.assert_called_once_with()
        username = fake_data.resource_inventory.get(
            constants.EON_RESOURCE_USERNAME)
        password = fake_data.resource_inventory.get(
            constants.EON_RESOURCE_PASSWORD)
        extra_args = {"extraVars": {
            "ansible_ssh_user": username,
            "ansible_ssh_pass": password,
            "hlmpassword": password
        }}
        calls = [call('hlm_ssh_configure',
                      fake_data.fake_id1, extra_args),
                 call('site', fake_data.fake_id1)]
        m_run_play.has_calls(calls)
        m_monitoring.assert_called_once_with()
        m_post_activation.assert_called_once_with(self.context,
                                              fake_data.fake_id1,
                                              fake_data.resource_inventory)
        self.assertEquals(m_run_wipe_disk.call_count, 1)

    @mock.patch('eon.common.ssh_utilities.RemoteConnection.'
                'exec_command_and_wait')
    def test_pre_activation_steps(self, mock_ssh):
        output = (0, "", "")
        mock_ssh.side_effect = [output, output]
        calls = [call("virsh list --all")]
        self.kvm_driver.pre_activation_steps(self.context,
                             resource_inventory=fake_data.kvm_resource_data)
        mock_ssh.assert_has_calls(calls)
