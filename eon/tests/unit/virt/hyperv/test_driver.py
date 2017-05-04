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

from eon.virt.hyperv import driver
from eon.virt import constants
from eon.tests.unit import fake_data
from eon.common import exception
from eon.tests.unit import base_test
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper


class TestDriver(base_test.TestCase):

    def setUp(self):
        super(TestDriver, self).setUp()
        self.hyperv_driver = driver.HyperVDriver()

    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    @mock.patch("eon.virt.common.utils.validate_nova_neutron_list")
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.get_hostname')
    def test_post_activation_steps(self, mocked_host_name,
                                   mocked_utils, mocked_pywinrm):
        context = {}
        id_ = "hyperv-compute"
        resource_inventory = fake_data.hyperv_resource_inventory
        mocked_host_name.return_value = "WIN23a01dasa1s"
        neutron_agent_type = constants.NEUTRON_AGENT_TYPE.get("hyperv")
        self.hyperv_driver.post_activation_steps(context, id_,
                                                 resource_inventory)

        mocked_host_name.assert_called_once_with()

        mocked_utils.assert_called_once_with(context, id_,
                self.hyperv_driver.db_api, "WIN23a01dasa1s",
                neutron_agent_type, constants.ACTIVATION)
        mocked_pywinrm.assert_called_once_with(resource_inventory[
            constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.'
                'HLMFacadeWrapper.get_pass_through')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_check_hyperv_host_using_pywinrm')
    def test_validate_create(self, m_check_con, m_pass_thru):
        m_pass_thru.return_value = fake_data.FAKE_PASS_THRU
        context = fake_data.FakeContext()
        data = self.hyperv_driver.validate_create(context,
                                              fake_data.create_data_hyperv)
        self.assertEquals(fake_data.create_data_hyperv, data,
                          "Invalid values returned")

    @mock.patch('eon.hlm_facade.hlm_facade_handler.'
                'HLMFacadeWrapper.get_pass_through')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_check_hyperv_host_using_pywinrm')
    def test_validate_create_exception(self, m_check_con, m_pass_thru):
        fake_passthru_hyperv_false = fake_data.FAKE_PASS_THRU
        fake_passthru_hyperv_false.get("global")["hyperv_cloud"] = "false"
        m_pass_thru.return_value = fake_passthru_hyperv_false
        context = fake_data.FakeContext()
        self.assertRaises(exception.UnsupportedDeployment,
                          self.hyperv_driver.validate_create,
                          context, fake_data.create_data_hyperv)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.'
                'HLMFacadeWrapper.get_pass_through')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_check_hyperv_host_using_pywinrm')
    def test_validate_create_exception2(self, m_check_con, m_pass_thru):
        fake_passthru_hyperv_false = fake_data.FAKE_PASS_THRU
        del fake_passthru_hyperv_false['global']['hyperv_cloud']
        m_pass_thru.return_value = fake_passthru_hyperv_false
        context = fake_data.FakeContext()
        self.assertRaises(exception.UnsupportedDeployment,
                          self.hyperv_driver.validate_create,
                          context, fake_data.create_data_hyperv)

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils'
                '.get_csv')
    def test_check_csv_exception_no_cluster_state(self, mock_get_csv):
        res_inv = {'ip_address': '10.10.10.10',
                   'port': 5986,
                   'username': 'user',
                   'password': 'password'
                  }
        mock_get_csv.return_value = ""
        self.assertRaises(exception.EonException,
                          self.hyperv_driver._check_csv,
                          res_inv)
        mock_get_csv.assert_called_once_with()

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.get_csv')
    def test_check_csv_exception_invalid_cluster_state(self, mock_get_csv):
        res_inv = {'ip_address': '10.10.10.10',
                   'port': 5986,
                   'username': 'user',
                   'password': 'password'
                  }
        mock_get_csv.return_value = "C:\ClusterStorage\Volume1"
        self.assertRaises(exception.EonException,
                          self.hyperv_driver._check_csv,
                          res_inv)
        mock_get_csv.assert_called_once_with()

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.get_csv')
    def test_check_csv_standalone(self, mock_get_csv):
        res_inv = {'ip_address': '10.10.10.10',
                   'port': 5986,
                   'username': 'user',
                   'password': 'password'
                  }
        mock_get_csv.return_value = "Standalone"
        self.hyperv_driver._check_csv(res_inv)
        mock_get_csv.assert_called_once_with()

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.get_csv')
    def test_check_csv_exception_valid_cluster(self, mock_get_csv):
        res_inv = {'ip_address': '10.10.10.10',
                   'port': 5986,
                   'username': 'user',
                   'password': 'password'
                  }
        mock_get_csv.return_value = "Cluster"
        self.hyperv_driver._check_csv(res_inv)
        mock_get_csv.assert_called_once_with()

    @mock.patch("eon.virt.common.utils.check_for_running_vms")
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.get_hostname')
    def test_pre_deactivation_steps(self, mocked_host_name, mocked_utils):
        context = {}
        resource_inventory = fake_data.hyperv_resource_inventory
        mocked_host_name.return_value = "WIN23a01dasa1s"
        self.hyperv_driver.pre_deactivation_steps(context,
                                resource_inventory=resource_inventory)
        mocked_host_name.assert_called_once_with()
        mocked_utils.assert_called_once_with(self.hyperv_driver, context,
                         "WIN23a01dasa1s", resource_inventory)

    def test_validate_delete(self):
        fake_data.res_mgr_data1["state"] = "provisioned"
        self.assertIsNone(self.hyperv_driver.validate_delete(
            fake_data.res_mgr_data1))

    def test_validate_delete_exception(self):
        fake_data.res_mgr_data1["state"] = "importing"
        self.assertRaises(exception.EonException,
                          self.hyperv_driver.validate_delete,
                          fake_data.res_mgr_data1)

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                'get_host_validation_data')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_check_hyperv_host_using_pywinrm')
    @mock.patch('eon.virt.hyperv.driver.HyperVDriver._check_csv')
    def test_pre_activation_steps(self, mocked_check_csv, mock_check_host,
                                  mocked_get_host_data):
        context = fake_data.FakeContext()
        validation_data = {u'iSCSI_initiator_service_state': True,
                           u'valid_compute_name': True,
                           u'hostname': u'WIN-4NAOV9N2DCH',
                           u'os_version': {u'Major': 6, u'MajorRevision': 0,
                                           u'MinorRevision': 0, u'Build': 9600,
                                           u'Minor': 3, u'Revision': 0},
                           u'ipaddresses': [
                               u'10.1.214.32', u'169.254.247.161',
                               u'169.254.205.230', u'12.12.12.69',
                               u'192.168.28.63', u'127.0.0.1'],
                           u'os_edition': {u'number': '8',
                                           u'name':
                                               u'Microsoft Windows Server'
                                               u' 2012 R2 Datacenter'},
                           u'vm_count': 0, u'host_date_configured': True}
        mocked_get_host_data.return_value = validation_data
        self.hyperv_driver.pre_activation_steps(
            context, resource_inventory=fake_data.create_data_hyperv)

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
                'create_server')
    @mock.patch('eon.virt.hyperv.driver.HyperVDriver._build_input_model_data')
    @mock.patch('eon.virt.hyperv.driver.HyperVDriver.post_activation_steps')
    @mock.patch('eon.openstack.common.lockutils.synchronized')
    def test_activate(self, m_lock, m_post, m_build, m_create,
                      m_commit, m_update, m_r_p,
                      m_c_r, m_r_d):
        self.hyperv_driver.activate(self.context,
                            fake_data.fake_id1,
                            fake_data.network_prop,
                            resource_inventory=fake_data.resource_inventory,
                            run_playbook=True)
        self.assertEquals(1, m_post.call_count)
        self.assertEquals(1, m_build.call_count)
        self.assertEquals(1, m_commit.call_count)
        self.assertEquals(2, m_update.call_count)
        self.assertEquals(1, m_r_p.call_count)
        self.assertEquals(1, m_c_r.call_count)
        self.assertEquals(1, m_r_d.call_count)

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
    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    @mock.patch('eon.openstack.common.lockutils.synchronized')
    def test_deactivate(self, m_lock, m_update, m_r_v, mrd, mcpr, mcc, mds):
        self.hyperv_driver.deactivate(self.context,
                            fake_data.fake_id1,
                            resource_inventory=fake_data.resource_inventory,
                            run_playbook=True)
        self.assertEquals(1, mrd.call_count)
        self.assertEquals(1, mcpr.call_count)
        self.assertEquals(1, mcc.call_count)
        self.assertEquals(1, mds.call_count)

    def test_check_compute_host_name_ex(self):
        validation_data = {}
        self.assertRaises(exception.EonException,
                  self.hyperv_driver._check_compute_host_name,
                          validation_data, fake_data.create_data_hyperv)

    def test_check_isci_initiator_service_ex(self):
        validation_data = {}
        self.assertRaises(exception.EonException,
                          self.hyperv_driver._check_isci_initiator_service,
                          validation_data, fake_data.create_data_hyperv)

    def test_check_date_from_controller_ex(self):
        validation_data = {}
        self.assertRaises(exception.EonException,
                          self.hyperv_driver._check_date_from_controller,
                          validation_data, fake_data.create_data_hyperv)

    def test_check_for_hyperv_version_ex(self):
        validation_data = {}
        self.assertRaises(exception.EonException,
                          self.hyperv_driver._check_for_hyperv_version,
                          validation_data, fake_data.create_data_hyperv)

    def test_check_for_hyperv_version_ex2(self):
        validation_data = {u'iSCSI_initiator_service_state': True,
                           u'valid_compute_name': True,
                           u'hostname': u'WIN-4NAOV9N2DCH',
                           u'os_version': {u'Major': 7, u'MajorRevision': 0,
                                           u'MinorRevision': 0, u'Build': 9600,
                                           u'Minor': 3, u'Revision': 0},
                           u'ipaddresses': [u'10.1.214.32', u'169.254.247.161',
                                            u'169.254.205.230', u'12.12.12.69',
                                            u'192.168.28.63', u'127.0.0.1'],
                           u'os_edition': {u'number': 8,
                                           u'name': u'Microsoft Windows Server'
                                                    u' 2012 R2 Datacenter'},
                           u'vm_count': 0,
                           u'host_date_configured': True}
        self.assertRaises(exception.HyperVHostUnSupportedOSError,
                          self.hyperv_driver._check_for_hyperv_version,
                          validation_data, fake_data.create_data_hyperv)

    def test_check_for_hyperv_version_ex3(self):
        validation_data = {u'iSCSI_initiator_service_state': True,
                           u'valid_compute_name': True,
                           u'hostname': u'WIN-4NAOV9N2DCH',
                           u'os_version': {u'Major': 6, u'MajorRevision': 0,
                                           u'MinorRevision': 0, u'Build': 9600,
                                           u'Minor': 3, u'Revision': 0},
                           u'ipaddresses': [u'10.1.214.32', u'169.254.247.161',
                                            u'169.254.205.230', u'12.12.12.69',
                                            u'192.168.28.63', u'127.0.0.1'],
                           u'os_edition': {u'number': 10,
                                           u'name': u'Microsoft Windows Server'
                                                    u' 2012 R2 Datacenter'},
                           u'vm_count': 0,
                           u'host_date_configured': True}
        self.assertRaises(exception.HyperVHostUnSupportedOSEditionError,
                          self.hyperv_driver._check_for_hyperv_version,
                          validation_data, fake_data.create_data_hyperv)

    def test_check_for_hyperv_version_ex4(self):
        validation_data = {u'iSCSI_initiator_service_state': True,
                           u'valid_compute_name': True,
                           u'hostname': u'WIN-4NAOV9N2DCH',
                           u'os_version': {u'Major': 6, u'MajorRevision': 0,
                                           u'MinorRevision': 0, u'Build': 9600,
                                           u'Minor': 3, u'Revision': 0},
                           u'ipaddresses': [u'10.1.214.32', u'169.254.247.161',
                                            u'169.254.205.230', u'12.12.12.69',
                                            u'192.168.28.63', u'127.0.0.1'],
                           u'vm_count': 0,
                           u'host_date_configured': True}
        self.assertRaises(exception.EonException,
                          self.hyperv_driver._check_for_hyperv_version,
                          validation_data, fake_data.create_data_hyperv)

    def test__check_for_instances_ex(self):
        validation_data = {u'iSCSI_initiator_service_state': True,
                           u'valid_compute_name': True,
                           u'hostname': u'WIN-4NAOV9N2DCH',
                           u'os_version': {u'Major': 6, u'MajorRevision': 0,
                                           u'MinorRevision': 0, u'Build': 9600,
                                           u'Minor': 3, u'Revision': 0},
                           u'ipaddresses': [u'10.1.214.32', u'169.254.247.161',
                                            u'169.254.205.230', u'12.12.12.69',
                                            u'192.168.28.63', u'127.0.0.1'],
                           u'os_edition': {u'number': 10,
                                           u'name': u'Microsoft Windows Server'
                                                    u' 2012 R2 Datacenter'},
                           u'vm_count': 10,
                           u'host_date_configured': True}
        self.hyperv_driver._check_for_instances(validation_data,
                                                fake_data.create_data_hyperv)

    def test__check_for_instances_ex2(self):
        validation_data = {}
        self.assertRaises(exception.WarningException,
                          self.hyperv_driver._check_for_instances,
                          validation_data, fake_data.create_data_hyperv)

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_connectivity_check')
    def test_validate_update(self, mocked_check):
        context = fake_data.FakeContext()
        updated_data = copy.deepcopy(fake_data.create_data_hyperv)
        updated_data['port'] = '5985'
        self.hyperv_driver.validate_update(context,
            fake_data.create_data_hyperv, updated_data)
        mocked_check.assert_called_once_with(updated_data,
                            fake_data.create_data_hyperv)

    @mock.patch('eon.virt.hyperv.driver.HyperVDriver.update_input_model')
    def test_update_success(self, m_update_in_model):
        context = {}
        res_data = copy.deepcopy(fake_data.hyperv_resource_inventory)
        res_data['state'] = "activated"
        m_update_in_model.return_value = mock.MagicMock()
        self.hyperv_driver.update(context, res_data, "id")
        m_update_in_model.assert_called_once_with(context, res_data, "id")

    @mock.patch('eon.virt.hyperv.driver.HyperVDriver.update_input_model')
    def test_update_success_provisioned_resource(self, m_update_in_model):
        context = {}
        res_data = fake_data.hyperv_resource_inventory
        m_update_in_model.return_value = mock.MagicMock()
        self.hyperv_driver.update(context, res_data, "id")
        assert m_update_in_model.call_count == 0

    @mock.patch('eon.virt.hyperv.driver.HyperVDriver.update_input_model')
    def test_update_exception(self, m_update_in_model):
        context = {}
        res_data = copy.deepcopy(fake_data.hyperv_resource_inventory)
        res_data['state'] = "activated"
        m_update_in_model.side_effect = exception.UpdateException()
        self.assertRaises(exception.UpdateException, self.hyperv_driver.update,
                          context, res_data, "id")
        m_update_in_model.assert_called_once_with(context, res_data, "id")

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch(
        'eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.'
                'HLMFacadeWrapper.update_server_by_id')
    @mock.patch('eon.virt.common.utils.VirtCommonUtils.modify_servers_payload')
    def test_update_input_model_exception(self, m_mod_payload, m_update_by_id,
                                          m_commit_changes, m_config_run,
                                          m_ready_deploy_run):
        context = {}
        input_mod_data = {"ansible_options": ""}
        m_mod_payload.return_value = input_mod_data
        m_update_by_id.return_value = mock.MagicMock()
        m_commit_changes.return_value = mock.MagicMock()
        m_config_run.return_value = mock.MagicMock()
        m_ready_deploy_run.side_effect = Exception()
        self.assertRaises(Exception, self.hyperv_driver.update_input_model,
                         context, fake_data.hyperv_resource_inventory, "id")
        m_update_by_id.assert_called_once_with(input_mod_data, "id")
        m_commit_changes.assert_called_once_with("id")
        m_config_run.assert_called_once_with()
        m_ready_deploy_run.assert_called_once_with()

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook_by_ids')
    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    @mock.patch(
        'eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.commit_changes')
    @mock.patch(
        'eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.delete_server')
    @mock.patch(
        'eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.revert_changes')
    def test__rollback_activate(self, m_rev, m_del, m_commit, m_update_prop,
                                m_r_p, m_r_c, m_r_d):
        context = fake_data.FakeContext()
        resource_inventory = {'name': "cs-ccp-compute-c0-clm",
                              "id": "ccn1-0001"}
        hux_obj = HLMFacadeWrapper(context)
        self.hyperv_driver._rollback_activate(context, hux_obj,
                                              resource_inventory,
                                              True)
        m_rev.assert_called_once_with()
        m_del.assert_called_once_with("ccn1-0001")
        m_commit.assert_called_once_with(
            "ccn1-0001", "Deactivate/Rollback HyperV compute resource")
