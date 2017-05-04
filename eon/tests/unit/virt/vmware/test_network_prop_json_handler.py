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
import mock
import copy
import json

from eon.virt.vmware import network_prop_json_handler
from eon.hlm_facade import hlm_facade_handler
from eon.tests.unit import fake_data
from eon.tests.unit import base_test


class TestNetworkPropJsonHandler(base_test.TestCase):

    def setUp(self):
        super(TestNetworkPropJsonHandler, self).setUp()
        self.context.auth_token = "auth_token"
        self.mocked_obj = mock.Mock()
        self.headers = {'X-Auth-Token': self.context.auth_token}

    def test_populate_network_properties_vlan(self):
        input_data = {"mgmt_trunk": {"name": "mgmt1",
                                      "nics": "vmnic0,vmnic1",
                                      "mtu": "1500"},
                      "cloud_trunks": [{"name": "cloudtrunk1",
                                        "nics": "vmnic2,vmnic3",
                                        "mtu": "1500",
                                        "network_name": "VLAN1-R1"}]
                      }
        lifecycle_manager = network_prop_json_handler.LifeCycleManager(
                                        "deployer_ip", "ssh_key",
                                        "user_name")
        with mock.patch.object(hlm_facade_handler,
            "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mocked_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_server_by_id"),
                mock.patch.object(self.hux, "get_networks"),
                mock.patch.object(self.hux, "get_network_groups"),
                mock.patch.object(self.hux, "get_interfaces_by_name"),
                mock.patch.object(network_prop_json_handler.utils,
                                  "get_global_pass_thru_data"),
                mock.patch.object(network_prop_json_handler,
                                  "_build_lifecycle_manager_info"),
                ) as(get_serv_id, get_net, get_ng,
                          get_intf_name, pass_thru_info, life_cycle_info):
                get_serv_id.return_value = fake_data.deployer_info
                get_net.return_value = fake_data.networks
                get_ng.return_value = fake_data.network_groups
                get_intf_name.return_value = fake_data.ovsvapp_interfaces
                pass_thru_info.return_value = ((fake_data.FAKE_PASS_THRU).
                                                get("global").get("hpecs"))
                life_cycle_info.return_value = lifecycle_manager

                net_json_str = (network_prop_json_handler.
                                populate_network_properties(self.context,
                                                            input_data))
                net_json = json.loads(net_json_str)
                network_type = (net_json['portGroups'][2]
                                ['cloud_network_type'])
                self.assertEquals(net_json["hlm_version"], "4.0")
                self.assertEquals(network_type, "vlan")
                self.assertEquals(len(net_json['switches']), 3)
                self.assertEquals(len(net_json['portGroups']), 4)
                self.assertEquals(net_json["esx_conf_net"]["start_ip"],
                                  "192.19.90.252")
                self.assertEquals(net_json["esx_conf_net"]["end_ip"],
                                  "192.19.90.253")
                self.assertEquals(net_json["esx_conf_net"]["gateway"],
                                  "12.12.12.10")

    def test_populate_network_properties_smaller_conf(self):
        input_data = {"mgmt_trunk": {"name": "mgmt1",
                                      "nics": "vmnic0,vmnic1",
                                      "mtu": "1500"},
                      "cloud_trunks": [{"name": "cloudtrunk1",
                                        "nics": "vmnic2,vmnic3",
                                        "mtu": "1500",
                                        "network_name": "VLAN1-R1"}]
                      }
        lifecycle_manager = network_prop_json_handler.LifeCycleManager(
                                        "deployer_ip", "ssh_key",
                                        "user_name")
        fake_networks = copy.deepcopy(fake_data.networks)
        fake_networks[0]['addresses'] = ["192.12.38.10-192.12.38.30"]
        with mock.patch.object(hlm_facade_handler,
            "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mocked_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_server_by_id"),
                mock.patch.object(self.hux, "get_networks"),
                mock.patch.object(self.hux, "get_network_groups"),
                mock.patch.object(self.hux, "get_interfaces_by_name"),
                mock.patch.object(network_prop_json_handler,
                                  "_build_lifecycle_manager_info"),
                ) as(get_serv_id, get_net, get_ng,
                          get_intf_name, life_cycle_info):
                get_serv_id.return_value = fake_data.deployer_info
                get_net.return_value = fake_networks
                get_ng.return_value = fake_data.network_groups
                get_intf_name.return_value = fake_data.ovsvapp_interfaces
                life_cycle_info.return_value = lifecycle_manager

                self.assertRaises(Exception,
                        network_prop_json_handler.populate_network_properties,
                        self.context, input_data)

    def test_populate_network_properties_vxlan_network(self):
        input_data = {"mgmt_trunk": {"name": "mgmt1",
                                      "nics": "vmnic0,vmnic1",
                                      "mtu": "1500"},
                      "cloud_trunks": [{"name": "cloudtrunk1",
                                        "nics": "vmnic2,vmnic3",
                                        "mtu": "1500",
                                        "network_name": "VxLAN-R1"}]
                      }
        lifecycle_manager = network_prop_json_handler.LifeCycleManager(
                                        "deployer_ip", "ssh_key",
                                        "user_name")
        with mock.patch.object(hlm_facade_handler,
            "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mocked_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_server_by_id"),
                mock.patch.object(self.hux, "get_networks"),
                mock.patch.object(self.hux, "get_network_groups"),
                mock.patch.object(self.hux, "get_interfaces_by_name"),
                mock.patch.object(network_prop_json_handler.utils,
                                  "get_global_pass_thru_data"),
                mock.patch.object(network_prop_json_handler,
                                  "_build_lifecycle_manager_info"),
                ) as(get_serv_id, get_net, get_ng,
                          get_intf_name, pass_thru_info, life_cycle_info):
                get_serv_id.return_value = fake_data.deployer_info
                get_net.return_value = fake_data.networks
                get_ng.return_value = fake_data.network_groups
                get_intf_name.return_value = fake_data.ovsvapp_interfaces
                pass_thru_info.return_value = ((fake_data.FAKE_PASS_THRU).
                                                get("global").get("hpecs"))
                life_cycle_info.return_value = lifecycle_manager

                net_json_str = (network_prop_json_handler.
                                populate_network_properties(self.context,
                                                            input_data))
                net_json = json.loads(net_json_str)
                network_type = (net_json['portGroups'][2]
                                ['cloud_network_type'])
                self.assertEquals(network_type, "vxlan")
