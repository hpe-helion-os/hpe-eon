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

import json
import mock
import contextlib
import requests

from eon.virt.vmware import driver
from eon.virt.vmware import utils
from mock import MagicMock
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
from eon.virt import constants
from eon.common import exception
from eon.deployer import driver as net_driver
from eon.virt.vmware import hlm_input_model
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.virt.vmware import validator
from eon.virt.common import utils as vir_utils
from oslo_config import cfg
import copy


CONF = cfg.CONF


class Prop(object):
    """Property Object base class."""

    def __init__(self):
        self.name = None
        self.value = None


class TestDriver(base_test.TestCase):

    def setUp(self):
        super(TestDriver, self).setUp()
        self.vc_driver = driver.VMwareVCDriver()
        self.comp_mock_driver = mock.MagicMock()
        self.net_mock_driver = mock.MagicMock()
        driver.eon.db = mock.MagicMock()
        self.mock_obj = mock.Mock()
        self.val = validator.ESXValidator(fake_data.resource_inventory)
        self.context = mock.MagicMock()
        self.vc_driver.hux_obj = HLMFacadeWrapper(self.context)

    def test_validate_create(self):
        context = fake_data.FakeContext()
        with mock.patch.object(self.vc_driver.vcm, "_get_session"):
            self.assertTrue(self.vc_driver.validate_create(
                context, fake_data.create_data))

    def test_monitor_events(self):
        self.assertIsNone(self.vc_driver.monitor_events('vc_data'))

    def test_validate_update(self):
        with contextlib.nested(
            mock.patch.object(self.vc_driver.vcm, "get_session"),
            mock.patch.object(self.vc_driver.vcm, "_get_session")
        ):
            self.assertTrue(self.vc_driver.validate_update(
                fake_data.update_data, fake_data.current_data))

    def test_validate_delete(self):
        self.assertIsNone(self.vc_driver.validate_delete(
            fake_data.res_mgr_data1))

    def test_auto_import_resources(self):
        with mock.patch.object(self.vc_driver,
                               "_get_cluster_id_mapping"):
            self.vc_driver.auto_import_resources(
                                        self.context,
                                        fake_data.create_data,
                                        'db_vc_rsrcs',
                                        'db_vc_rscrc_prop')

    def test__update_input_model(self):
        id_ = "123"
        server = [{'id': 123}, {'id': 456}]
        pass_thru = fake_data.updated_pass_thru
        input_data = fake_data.input_data
        with contextlib.nested(
            mock.patch.object(self.vc_driver, "_add_servers"),
            mock.patch.object(self.vc_driver, "_update_pass_through")
            ) as (add_serv, upd_pass_thru):
            add_serv.return_value = server
            upd_pass_thru.return_value = pass_thru
            serv = self.vc_driver._add_servers(id_, input_data)
            self.assertEquals(serv, server)

    def test__update_pass_through(self):
        id_ = "1234"
        with contextlib.nested(
            mock.patch.object(self.vc_driver.hux_obj, "get_pass_through"),
            mock.patch.object(self.vc_driver.hux_obj, "update_pass_through")
            ) as (get_pass_thru, upd_pass_thru):
            get_pass_thru.return_value = fake_data.pass_thru_with_global
            upd_pass_thru.return_value = fake_data.updated_pass_thru
            res = self.vc_driver._update_pass_through(id_, fake_data.pass_thru)
            self.assertEquals(res, fake_data.updated_pass_thru)

    def test__add_servers(self):
        id_ = "123"
        expec_data = [{'id': 123}, {'id': 456}]
        servers_data = {"servers": [{"id": 123}, {"id": 456}]}
        with mock.patch.object(self.vc_driver.hux_obj,
                                "update_server_by_id") as update:
            update.return_value = None
            serv = self.vc_driver._add_servers(id_, servers_data)
            self.assertEquals(serv, expec_data)

    def test_get_host_list(self):
        resource_inventory = {"name": "esx-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "inventory": {"datacenter": {"name":
                                                            "dc_name"},
                                            "hosts": [{"name": "10.1.214.177"},
                                                      {"name": "10.1.214.178"}
                                                      ],
                                            "DRS": "enabled"
                                           }
                              }
        expec_val = [u'10.1.214.177', u'10.1.214.178']
        value = self.vc_driver.get_host_list(resource_inventory)
        self.assertEquals(expec_val, value)

    def test_build_input_model_data_for_new_hosts(self):
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        expec = {
            'pass_through': {
                'pass-through': {
                    'global': {'vmware': [cluster_data[
                        'resource_manager_info']]},
                    'servers': ['data', 'id', 'data', 'id']
                }
            },
            'servers': {
                'servers': [{
                    'SERVER_ID': 'server_id',
                    'SERVER_IPADDR': '10.10.10.10',
                    'SERVER_ROLE': 'server_role_name'
                }, {
                    'SERVER_ID': 'server_id',
                    'SERVER_IPADDR': '10.10.10.10',
                    'SERVER_ROLE': 'server_role_name'
                }]
            }
        }
        ovsvapp_list = [{'status': 'success', 'host-moid': u'host-459',
            'ovsvapp_node': 'ovsvapp-10-1-221-78'}, {}]
        passthrough_info = {"key": "value"}
        ovsvapp_passthrough_info = {'id': 'server_id',
                                    'data': passthrough_info
                                    }
        db_api = self.vc_driver.db_api
        prop = Prop()
        prop.value = json.dumps({"hlm_prop": "val1", "network_driver":
                                 {"cluster_dvs_mapping": "mapping"}}, )
        network_driver = [{"SERVER_ID": "server_id",
                        "SERVER_IPADDR": "10.10.10.10",
                        "SERVER_ROLE": "server_role_name"}]
        with contextlib.nested(
            mock.patch.object(db_api, "get_properties"),
            mock.patch.object(hlm_input_model, "_build_network_driver_info"),
            mock.patch.object(hlm_input_model,
                               "_build_ovsvapp_passthrough_info"),
            )as (get_prop, build_net_driv, build_ovsvapp_passthru):
            get_prop.return_value = [prop]
            build_net_driv.return_value = network_driver
            build_ovsvapp_passthru.return_value = ovsvapp_passthrough_info
            result = self.vc_driver.build_input_model_data_for_new_hosts(
                         self.context, cluster_data, ovsvapp_list)
            self.assertEquals(expec, result)

    def test_roll_back_host_info(self):
        db_api = self.vc_driver.db_api
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        current_hosts_list = [{'name': 1}, {'name': 2}]
        prop = Prop()
        prop.value = json.dumps({"hlm_prop": "val1", "network_driver":
                                 {"cluster_dvs_mapping": "mapping",
                                  'name': ['network_driver_name']}}, )
        ret = ['network_driver_name']
        with contextlib.nested(
            mock.patch.object(db_api, "get_properties"),
            mock.patch.object(utils, "strip_current_ovsvapp_host_info")
            ) as (get_prop, strip_curr_ovsvapp):
            get_prop.return_value = [prop]
            strip_curr_ovsvapp.return_value = ret
            result = self.vc_driver.roll_back_host_info(self.context,
                                         current_hosts_list, cluster_data)
            self.assertEquals(None, result)

    def test_get_cluster_id_mapping(self):
        db_vc_resources = [{"name": "cluster1", "type": "esxcluster",
                            "id": "1234", "state": "activated"}]
        db_vc_resources_prop = {"1234": [{"id": "456", "key": "cluster_moid",
                                          "value": "domain-20"}]}
        cluster_list = self.vc_driver._get_cluster_id_mapping(db_vc_resources,
                                          db_vc_resources_prop)
        self.assertEquals(cluster_list[0], ("1234", 'domain-20'))

    def test_get_inventory(self):
        with mock.patch.object(self.vc_driver.vcm,
                               "get_vcenter_inventory_collector"):
            self.assertTrue(self.vc_driver.get_inventory(
                fake_data.create_data))

    def test_get_res_inventory(self):
        res_mgr_data = fake_data.res_mgr_info_dict
        res_property_obj = mock.MagicMock()
        with mock.patch.object(self.vc_driver.vcm,
                               "get_vcenter_inventory_collector"):
            self.vc_driver.get_res_inventory(res_mgr_data, res_property_obj)

    def test_get_res_inventory_none(self):
        res_mgr_data = fake_data.res_mgr_info_dict
        res_property_obj = mock.MagicMock()
        with mock.patch.object(self.vc_driver.vcm,
                               "get_vcenter_inventory_collector") as get_vc:
            get_vc.return_value = None
            self.assertEqual({},
                self.vc_driver.get_res_inventory(res_mgr_data,
                                                 res_property_obj))

    def test_remove(self):
        resource_type = constants.EON_RESOURCE_TYPE_ESX_CLUSTER
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        with contextlib.nested(
            mock.patch.object(self.vc_driver, "get_network_properties"),
            mock.patch.object(utils, "get_cluster_property"),
            mock.patch.object(net_driver, "load_resource_network_driver"),
            mock.patch.object(net_driver, "load_resource_compute_driver"),
            mock.patch.object(self.vc_driver.db_api, "delete_property")
            ) as (get_net_props, _get_cl, x, y, _):
            x.return_value = self.net_mock_driver
            y.return_value = self.comp_mock_driver
            _get_cl.return_value = fake_data.cluster_moid1
            self.vc_driver.remove(self.context, resource_type, cluster_data)
            get_net_props.assert_called_once_with(self.context,
                            cluster_data["resource_manager_info"],
                            cluster_data)
            _get_cl.assert_called_once_with(cluster_data,
                                            constants.CLUSTER_MOID)

    def _get_info(self):
        proxy_info = {"name": "proxynode"}
        nw_info = [{"name": "ovsvappnode"}]
        return (proxy_info, nw_info)

    def test_build_input_model_data(self):
        db_api = self.vc_driver.db_api
        cluster_data = [{"id": "1234", "resource_manager_info": {}}]
        prop = Prop()
        prop.value = json.dumps({"hlm_prop": "val1"})
        with contextlib.nested(
            mock.patch.object(db_api, "get_properties"),
            mock.patch.object(hlm_input_model, "build_servers_info"),
            mock.patch.object(hlm_input_model, "build_passthrough_info"),
            ) as (get_prop, build_server, build_pass):
            get_prop.return_value = [prop]
            build_server.return_value = self._get_info()
            build_pass.return_value = self._get_info()
            input_model = self.vc_driver.build_input_model_data("context",
                                                  "add",
                                                  cluster_data,
                                                  "input_model_data")
            server = input_model['servers']['servers'][0]
            pass_thru = (input_model['pass_through']['pass-through']
                                                        ['servers'][0])
            self.assertEquals(pass_thru['name'], "proxynode")
            self.assertEquals(server['name'], "proxynode")

    def test__check_for_active_clusters_with_no_active_clusters(self):
        db_api = self.vc_driver.db_api
        with contextlib.nested(
            mock.patch.object(self.vc_driver, "get_inventory"),
            mock.patch.object(db_api, "get_all_resources"),
                               ) as (get_inv, get_all_res):
            get_all_res.return_value = fake_data.fake_db_clusters_imported
            self.assertEqual(False,
            self.vc_driver._check_for_active_clusters(self.context,
                fake_data.cluster_data_remove, constants.EXPECTED_STATE))
            get_inv.assert_called_once_with(
                fake_data.cluster_data_remove["resource_manager_info"])

    def test__check_for_active_clusters_with_active_clusters(self):
        clus_d = copy.deepcopy(fake_data.cluster_data_remove)
        db_api = self.vc_driver.db_api
        with contextlib.nested(
            mock.patch.object(self.vc_driver, "get_inventory"),
            mock.patch.object(db_api, "get_all_resources"),
                               ) as (get_inv, get_all_res):
            get_inv.return_value = fake_data.vc_inventory
            get_all_res.return_value = fake_data.fake_db_clusters_activated
            self.assertEqual(True,
            self.vc_driver._check_for_active_clusters(self.context,
                clus_d, constants.EXPECTED_STATE))
            get_inv.assert_called_once_with(
                clus_d["resource_manager_info"])

    def test_host_commissioning(self):
        clus_d = copy.deepcopy(fake_data.cluster_data_remove)
        network_prop = fake_data.network_prop
        prop = Prop()
        prop.value = json.dumps({"hlm_prop": "val1",
                                 "network_driver": {"cluster-1": []}})
        with contextlib.nested(
            mock.patch.object(utils, "frame_provision_data"),
            mock.patch.object(self.vc_driver, "_update_state"),
            mock.patch.object(net_driver, "load_resource_network_driver"),
            mock.patch.object(self.vc_driver.db_api, "get_properties"),
            mock.patch.object(self.vc_driver.db_api, "update_property"),
                               ) as (_, update_st, load_net, get_prop,
                                     update_prop):
            load_net.create.return_value = (
                fake_data.host_commision_network_info)
            get_prop.return_value = [prop]
            self.vc_driver.host_commission(self.context, clus_d["type"],
                                           clus_d, network_prop)
            update_prop.assert_called_once_with(self.context,
                                                "update-property",
                                                fake_data.fake_id1,
                                                "hlm_properties",
                                                prop.value)
            update_st.assert_called_once_with(self.context, fake_data.fake_id1,
                                              "host-commissioning")

    def test_get_hypervisor_hostname(self):
        hostname = 'domain-c7.vcenter_id'
        self.assertEquals(hostname, self.vc_driver.
            get_hypervisor_hostname(fake_data.resource_inventory1))

    def test_pre_activation_steps_failure_missing_config_json(self):
        context = mock.MagicMock()
        data = {}
        resource_inventory = {"name": "esx-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "inventory": {"datacenter": {"name":
                                                            "dc_name"},
                                            "hosts": [{"vms": 1}],
                                            "DRS": "enabled"
                                           }
                              }
        with contextlib.nested(
            mock.patch.object(self.vc_driver, "get_dc_network_properties"),
            mock.patch.object(self.val, "validate_cluster")
                ) as (dc_net_prop, val_clust):
            dc_net_prop.return_value = None
            val_clust.return_value = mock.MagicMock()
            self.assertRaises(exception.ActivationFailure,
                              self.vc_driver.pre_activation_steps,
                              context,
                              resource_inventory=resource_inventory,
                              data=data)

    def test_get_neutron_url(self):
        context = MagicMock()
        url = CONF.neutron.url
        neutron_url = vir_utils.get_neutron_url(context)
        self.assertEquals(url, neutron_url)

    def test_delete_neutron_service_success(self):
        context = MagicMock()
        headers = {}
        resource_inventory = {"name": "esx-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "inventory": {"datacenter": {"name":
                                                            "dc_name"},
                                            "hosts": [{"name": "10.1.214.177"},
                                                      {"name": "10.1.214.177"}
                                                      ],
                                            "DRS": "enabled"
                                           }
                              }
        url = "http://10.10.10.10:8774/v2/tenant_id/os-services/1234"
        with contextlib.nested(
                mock.patch.object(vir_utils, "get_neutron_url"),
                mock.patch.object(vir_utils, "get_neutron_agent_list"),
                mock.patch.object(self.vc_driver, "get_host_list"),
                mock.patch.object(vir_utils,
                                   "get_neutron_agent_rest_api"),
                mock.patch.object(requests, "delete")
                ) as(neut_url, neut_agent_list, host_list,
                      neut_rest_api, req_d):
            neut_url.return_value = url
            neut_agent_list.return_value = fake_data.agents
            host_list.return_value = ["10.1.214.177", "10.1.214.178"]
            neut_rest_api.return_value = (url, headers)
            fake_response = self.mock_obj
            fake_response.status_code = 204
            req_d.return_value = fake_response
            nova_result = self.vc_driver.delete_neutron_service(context,
                                                         resource_inventory)
            self.assertTrue(nova_result)

    def test_pre_activation_steps_success(self):
        context = mock.MagicMock()
        data = {"key": "value"}
        resource_inventory = {"name": "esx-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "inventory": {"datacenter": {"name": "dc_name"},
                                            "hosts": [{"vms": 0}],
                                            "DRS": "enabled"
                                           }
                              }
        with contextlib.nested(
            mock.patch.object(self.vc_driver, "get_dc_network_properties"),
            mock.patch.object(self.val, "validate_cluster")
                ) as (dc_net_prop, val_clust):
            dc_net_prop.return_value = None
            val_clust.return_value = mock.MagicMock()
            self.assertEquals(None, self.vc_driver.pre_activation_steps
                              (context,
                               resource_inventory=resource_inventory,
                               data=data))

    @mock.patch("eon.virt.common.utils.check_for_running_vms")
    @mock.patch(
        'eon.virt.vmware.driver.VMwareVCDriver.get_hypervisor_hostname')
    def test_pre_deactivation_steps(self, mocked_host_name, mocked_utils):
        context = {}
        resource_inventory = fake_data.esx_resource_inventory
        mocked_host_name.return_value = "esx_host_name"
        self.vc_driver.pre_deactivation_steps(context,
                        resource_inventory=resource_inventory)
        mocked_host_name.assert_called_once_with(resource_inventory)
        mocked_utils.assert_called_once_with(self.vc_driver, context,
                         "esx_host_name", resource_inventory)

    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.'
                'post_activation_steps')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_playbook_by_ids')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'run_monitoring_playbooks')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.build_input_model_data')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._run_cp_playbooks')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._update_input_model')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.set_network_properties')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.provision')
    def test_activate(self, m_prov, m_set_net, m_up_model, m_run, m_bimd,
                      r_m_p, m_c_c, m_c_r, m_r_d, m_r_p, m_p_s):
        m_bimd.return_value = fake_data.pass_through
        ret_value = self.vc_driver.activate(self.context,
                                        fake_data.fake_id1,
                                        fake_data.network_prop,
                                        input_model_info=
                                            fake_data.pass_through,
                                        resource_inventory=
                                            fake_data.resource_inventory1,
                                        run_playbook=True)
        self.assertEqual(None, ret_value)
        m_up_model.assert_called_once_with(fake_data.fake_id1,
                                           fake_data.pass_through)

    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._run_cp_playbooks')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._stop_compute_services')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._update_input_model')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.build_input_model_data')
    @mock.patch('eon.hlm_facade.http_requests.get')
    @mock.patch('eon.hlm_facade.http_requests.put')
    @mock.patch('eon.hlm_facade.http_requests.post')
    @mock.patch('eon.hlm_facade.http_requests.delete')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.provision')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.set_network_properties')
    def test_activate_exception(self, m_set_net, m_prov, md, mpo, mpu,
                                mgm, m_bimd, m_update, m_stop, m_cp):
        m_bimd.return_value = fake_data.pass_through
        m_cp.side_effect = Exception
        self.assertRaises(Exception, self.vc_driver.activate,
                          self.context,
                          fake_data.fake_id1,
                          fake_data.network_prop,
                          input_model_info=fake_data.pass_through,
                          resource_inventory=
                          fake_data.resource_inventory1,
                          run_playbook=True)
        self.assertEquals(2, md.call_count)
        self.assertEquals(2, mpo.call_count)
        self.assertEquals(1, mpu.call_count)
        self.assertEquals(1, mgm.call_count)

    @mock.patch(
        'eon.virt.vmware.driver.VMwareVCDriver.delete_network_properties')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.remove')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._delete_pass_through')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'delete_server')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'revert_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'config_processor_run')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'ready_deployment')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.build_input_model_data')
    def test_deactivate(self, m_bimd, mrd, mcpr, mcc, mrc, mds, mdps, mrem,
                        mdel_net):
        m_bimd.return_value = fake_data.pass_through
        self.vc_driver.deactivate(self.context,
                                  fake_data.fake_id1,
                                  resource_inventory=
                                  fake_data.resource_inventory_deactivate,
                                  run_playbook=True,
                                  force_deactivate=True)
        self.assertEquals(1, mrd.call_count)
        self.assertEquals(1, mcpr.call_count)
        self.assertEquals(1, mcc.call_count)
        self.assertEquals(1, mds.call_count)
        self.assertEquals(1, mdps.call_count)

    @mock.patch(
        'eon.virt.vmware.driver.VMwareVCDriver.delete_network_properties')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.remove')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'delete_server')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'revert_changes')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.build_input_model_data')
    def test_deactivate_exception(self, mbimd, mrc, mds, mrem,
                        mdel_net):
        mbimd.return_value = fake_data.pass_through
        mds.side_effect = Exception
        self.vc_driver.deactivate(
                                  self.context,
                                  fake_data.fake_id1,
                                  resource_inventory=
                                  fake_data.resource_inventory_deactivate,
                                  run_playbook=True,
                                  force_deactivate=False)
        self.assertEquals(1, mrc.call_count)

    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.build_input_model_data')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.'
                '_invoke_activate_playbooks')
    def test_update(self, m_ia_play, mcc, m_build):
        m_build.return_value = fake_data.pass_through
        self.vc_driver.update(self.context,
                              fake_data.fake_id1,
                              input_model_info=
                              fake_data.pass_through,
                              resource_inventory=
                              fake_data.resource_inventory1)

    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.'
                'build_input_model_data_for_new_hosts')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._update_state')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver._update_input_model')
    @mock.patch('eon.virt.vmware.driver.VMwareVCDriver.'
                '_invoke_activate_playbooks')
    def test_host_commission_model_changes(self, miapi, m_up_model, mus,
                                           m_bimd):
        m_bimd.return_value = fake_data.pass_through
        self.vc_driver.host_commission_model_changes(
            self.context,
            fake_data.fake_id1,
            hosts_data=fake_data.pass_through,
            resource_inventory=fake_data.resource_inventory1)
        miapi.assert_called_once_with(self.context,
                                      fake_data.fake_id1,
                                      fake_data.pass_through,
                                      True)
        mus.assert_called_once_with(self.context,
                                    fake_data.fake_id1,
                                    'activating')

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'get_pass_through')
    @mock.patch('eon.virt.common.utils.get_encrypted_password')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_pass_through')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    def test_create_update_vc_pass_through(self, mock_commit, mock_update_pt,
                                           mock_pass, mock_get_pt):
        mock_pass.return_value = 'mock-encrypted-pass'
        mock_get_pt.return_value = fake_data.empty_pass_thru_vc
        self.vc_driver.update_vc_pass_through(self.context,
                                              fake_data.res_mgr_data1)
        mock_get_pt.assert_called_once()
        mock_pass.assert_called_once_with(
            fake_data.res_mgr_data1.get('password'))
        mock_update_pt.assert_called_once()
        task = "vCenter %s Create" % fake_data.res_mgr_data1.get("name")
        mock_commit.assert_called_once_with(fake_data.res_mgr_data1.get("id"),
                                            task)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'get_pass_through')
    @mock.patch('eon.virt.common.utils.get_encrypted_password')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_pass_through')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    def test_update_update_vc_pass_through(self, mock_commit, mock_update_pt,
                                           mock_pass, mock_get_pt):
        mock_pass.return_value = 'mock-encrypted-pass'
        mock_get_pt.return_value = fake_data.pass_thru_vc
        self.vc_driver.update_vc_pass_through(self.context,
                                              fake_data.res_mgr_data1)
        mock_get_pt.assert_called_once()
        mock_pass.assert_called_once_with(
            fake_data.res_mgr_data1.get('password'))
        mock_update_pt.assert_called_once()
        task = "vCenter %s Update" % fake_data.res_mgr_data1.get("name")
        mock_commit.assert_called_once_with(fake_data.res_mgr_data1.get("id"),
                                            task)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'get_pass_through')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'update_pass_through')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    def test_delete_vc_pass_through(self, mock_commit, mock_update_pt,
                                    mock_get_pt):
        mock_get_pt.return_value = copy.deepcopy(fake_data.pass_thru_vc)
        vcenter_id = fake_data.res_mgr_data1.get("id")
        self.vc_driver.delete_vc_pass_through(
            self.context, fake_data.res_mgr_data1)
        task = "vCenter %s Delete" % fake_data.res_mgr_data1.get("name")
        mock_get_pt.assert_called_once()
        mock_update_pt.assert_called_once()
        mock_commit.assert_called_once_with(vcenter_id, task)
