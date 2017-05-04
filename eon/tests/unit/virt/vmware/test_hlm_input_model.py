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

from eon.virt.vmware import hlm_input_model
from testtools import TestCase


class TestHlmInputModel(TestCase):

    def setUp(self):
        super(TestHlmInputModel, self).setUp()

    def _build_proxy_ovsvapp_info(self):
        info = {"computeproxy": {"name": "cluster1",
                                 "pxe-ip-addr": "10.1.215.5",
                                 "cluster_moid": "domain-20"
                                },
                 "network_driver": {"cluster1": [{"name": "ovs-vapp1",
                                                "pxe-ip-addr": "10.1.215.6",
                                                "esx_hostname": "esx_hostname",
                                                "host-moid": "host-123"}
                                            ],
                                    "cluster_dvs_mapping":
                                        "cluster_dvs_mapping",
                                    }
                }
        return info

    def _build_cluster_data(self):
        cluster_data = {"name": "cluster1",
                        "resource_manager_info": {"id": "1234",
                                 "ip_address": "10.1.215.7",
                                 "password": "password",
                                 "username": "username",
                                 "port": "443"},
                        }
        return cluster_data

    def test_build_servers_info(self):
        cluster_data = self._build_cluster_data()
        input_model_data = {"server_group": "server-group"}
        info = self._build_proxy_ovsvapp_info()
        (proxy_info, ovsvapp_info) = hlm_input_model.build_servers_info(info,
                                                            "add",
                                                            cluster_data,
                                                            input_model_data)
        self.assertEquals(proxy_info['ip-addr'], "10.1.215.5")
        self.assertEquals(ovsvapp_info[0]['ip-addr'], "10.1.215.6")

    def test_build_passthrough_info(self):
        cluster_data = self._build_cluster_data()
        info = self._build_proxy_ovsvapp_info()
        (proxy_info, ovsvapp_info) = hlm_input_model.build_passthrough_info(
            info, cluster_data)
        vmware_info = proxy_info['data']['vmware']
        ovsvapp_vmware_info = ovsvapp_info[0]['data']['vmware']
        self.assertEquals(vmware_info['vcenter_cluster'], "cluster1")
        self.assertEquals(ovsvapp_vmware_info['cluster_dvs_mapping'],
                          "cluster_dvs_mapping")
        self.assertEquals(ovsvapp_vmware_info['esx_hostname'],
                          "esx_hostname")
