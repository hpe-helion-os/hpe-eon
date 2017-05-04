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
import mock
import json
import uuid
from eon.virt import constants
import copy


fake_id1 = str(uuid.uuid4())
fake_id2 = str(uuid.uuid4())
fake_res_id1 = str(uuid.uuid4())
cont = [{"name": "ccp"}]
control_plane_name = cont[0].get("name")

empty_pass_thru_vc = {'servers': [], 'global': {}}

pass_thru_vc = {"global": {
    "vmware": [
        {
            "username": "root",
            "cert_check": False,
            "ip": "10.1.221.80",
            "password": "pass123",
            "port": "443",
            "id": fake_id1
        }
    ]
},
    "servers": [
        {
            "data": {
                "vmware": {
                    "vcenter_cluster": "compute-blade",
                    "vcenter_id": fake_id1
                }
            },
            "id": "67c7d8e661b408d63a245bb4e244a1484c43fb7b"
        },
        {
            "data": {
                "vmware": {
                    "vcenter_cluster": "compute-blade",
                    "cluster_dvs_mapping":
                        "dc1/host/compute-blade:TRUNK-DVS-compute-blade",
                    "esx_hostname": "10.1.221.76",
                    "vcenter_id": fake_id1
                }
            },
            "id": "24032b031d26263d3090df49b4974e357d43c2c4"
        }
    ]
}

pass_thru = {'pass-through': {
    'servers': [{
        'data': {
            'vmware': {
                'vcenter_id':
                    'DF504912-9468-45FD-BEF7-9332BE70DBB5',
                'vcenter_cluster': 'Cluster',
            }
        },
        'id': '1234'
    }
    ]
}
}

input_data = {"servers": [{"id": 123}, {"id": 456}],
              'pass-through': {
                  'servers': [{
                      'data': {
                          'vmware': {
                              'vcenter_id':
                                  'DF504912-9468-45FD-BEF7-9332BE70DBB5',
                              'vcenter_cluster': 'Cluster',
                          }
                      },
                      'id': '1234'
                  }
                  ]
              }
              }

pass_thru_with_global = {"global": {
    "vmware": [
        {
            "username": "root",
            "cert_check": False,
            "ip": "10.1.221.80",
            "password": "pass123",
            "port": "443",
            "id": fake_id1
        }
    ]
},
    'servers': []
}

updated_pass_thru = {"global": {
    "vmware": [
        {
            "username": "root",
            "cert_check": False,
            "ip": "10.1.221.80",
            "password": "pass123",
            "port": "443",
            "id": fake_id1
        }
    ]
},
    'servers': [{
        'data': {
            'vmware': {
                'vcenter_id': 'DF504912-9468-45FD-BEF7-9332BE70DBB5',
                'vcenter_cluster': 'Cluster',
            }
        },
        'id': '1234'
    }]
}

create_data = {
              "name": "vcenter1",
              "port": "443",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "password",
              "type": "vcenter"
              }

create_data_hyperv = {
              "name": "hyperv",
              "port": "5986",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "password",
              "type": "hyperv"
              }

baremetal_create_data = {
              "name": "bm",
              "port": "443",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "password",
              "type": "baremetal",
              "ilo_ip": "10.1.21.1",
              "ilo_password": "password",
              "ilo_user": "user",
              "mac_addr": "ma:ya:nk"
              }

baremetal_create_data_fail = {
              "name": "bm",
              "port": "443",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "password",
              "type": "baremetal",
              "ilo_ip": "10.1.21.1",
              "ilo_user": "user"
              }

hyperv_resource_inventory = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": 5986
                            }

kvm_resource_inventory = {"name": "rhelcompute",
                          "ip_address": "12.12.12.69",
                          "username": "stack",
                          "password": "password",
                          "EON_RESOURCE_NAME": "rhel"}

esx_resource_inventory = {"name": "esx-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password"
                              }

kvm_create_data = {
              "name": "rhel_compute",
              "port": "443",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "password",
              "type": "rhel",
              }

kvm_create_data_fail = {
              "name": "hlinux_compute",
              "port": "443",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "password",
              "type": "hlinux",
              "mac_addr": "ma:ya:nk",
              "ilo_ip": "10.1.21.1",
              }

update_data = {
              "name": "vcenter2",
              "port": "443",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "password",
              "type": "vcenter"
              }

current_data = create_data

insufficient_create_data = {
              "port": "443",
              "ip_address": "10.1.192.98",
              "username": "username",
              "type": "vcenter"
              }

invalid_create_data = {
              "port": "443",
              "name": "vcenter1",
              "ip_address": "10.1.192.98",
              "username": "username",
              "password": "",
              "type": "vcenter"
              }

res_mgr_data1 = {
                "name": "vcenter1",
                "id": fake_id1,
                "port": "443",
                "ip_address": "10.1.192.98",
                "username": "username",
                "password": "password",
                "type": "vcenter"
                }
res_mgr_data2 = {
                "name": "vcenter2",
                "id": fake_id2,
                "port": "443",
                "ip_address": "10.1.192.99",
                "username": "username",
                "password": "password",
                "type": "vcenter"}
res_data = {
            "name": "test",
            "id": fake_id1,
            "mac_addr": "ma:ya:nk",
            "ilo_ip": "10.1.221.1"}

activate_data = {"network_info": {}}
cluster_data_remove = {"resource_manager_info": {
                            "id": 1},
                       "inventory": {"datacenter": {"name": "dc-1",
                                                    "moid": "dc-1"}},
                       "name": "cluster-1",
                       "type": "esxcluster",
                       "id": fake_id1}

cluster_data = copy.deepcopy(cluster_data_remove)

vc_inventory = {"resources": {"datacenter":
                    {"count": 1,
                     "dc-1":
                     {"clusters":
                      {"name": "cluster2"}}}}}

cluster_moid1 = "domain-c1"
vc_data_remove = {'cluster': 'cluster-1',
                  'cluster_moid': cluster_moid1,
                  'datacenter': 'dc-1',
                   "id": 1,
                  }
get_all_res = [res_mgr_data1, res_mgr_data2]

get_res_properties_cluster = [{"key": "cluster_moid", "value":
                               "domain1", "parent_id": fake_id1}]

res_data_db_cluster = {"username": "UNSET",
                    "name": "Mgmt",
                    "type": "esxcluster",
                    "port": "UNSET",
                    "password": "password",
                    "ip_address": "UNSET",
                    "id": fake_res_id1}
metadata_dict = {"meta_data": []}
res_data_cluster_resp = dict(res_data_db_cluster.items() +
                             metadata_dict.items())

res_mgr_info_dict = {constants.RSRC_MGR_INFO: res_mgr_data1}

get_with_inventory_cluster = dict(res_data_cluster_resp.items() +
                                  res_mgr_info_dict.items())
host_moid1 = "host-1"
host_fake_inv_data1 = {'hosts':
    [{'connection_state': 'connected', 'moid': host_moid1,
      'name': '10.1.1.1', 'vms': 0}]}

sample_inventory = {("HostSystem", host_moid1):
                    {"name": "10.1.1.1",
                     "parent": mock.MagicMock(type=dict),
                     "runtime.connectionState": "connected"}}

sample_inventory_with_vms = {("HostSystem", host_moid1):
                             {"name": "10.1.1.1",
                             "runtime.connectionState": "connected",
                             "vm": [mock.ANY]}}

network_prop = {"vm_config": [{}],
                "lifecycle_manager": {"hlm_version": "4.0.0"},
                "template_info": {"upload_to_cluster": False}}

network_prop1 = {
                "switches": [{}],
                "portGroups": [{}]}

cluster_net_prop = {"portGroups": [{}],
                    "switches": [{}]}

fake_db_clusters_imported = [{"name": "cluster1", "state": "imported"},
                    {"name": "cluster2", "state": "imported"}]

fake_db_clusters_activated = [{"name": "cluster-1", "state": "imported"},
                    {"name": "cluster2", "state": "activated"}]

host_commision_network_info = {
                "compute":
                        [{'status': 'failed', 'host-moid': u'host-459',
                        'status_msg': 'Error',
                        'esx_hostname': '10.1.221.78'},
                         ]}

resource_inventory = {"resource_manager_info": {},
                       "inventory": {"datacenter": {"name": "dc-1"}},
                       "name": "cluster-1",
                       "type": "esxcluster",
                       "state": "activated",
                       "id": fake_id1,
                       "username": "stack",
                       "password": "stack"}

resource_inventory_deactivate = {"resource_manager_info": {},
                       "inventory": {"datacenter": {"name": "dc-1"}},
                       "name": "cluster-1",
                       "type": "esxcluster",
                       "state": "deactivating",
                       "id": fake_id1}

resource_inventory1 = {"resource_manager_info": {},
                       "inventory": {"datacenter": {"name": "dc-1"}},
                       "name": "cluster-1",
                       "type": "esxcluster",
                       "state": "activated",
                       "id": fake_id1,
                       "meta_data": [{
                                        'name': 'cluster_moid',
                                        'value': 'domain-c7',
                                        'id':
                                        '45a3707e-b1b7-4d93-8066-6689e4d90f51'
                                    }],
                       "cluster_moid": "domain_id",
                       "resource_mgr_id": "vcenter_id"}

resource_inventory2 = {"resource_manager_info": {},
                       "inventory": {"datacenter": {"name": "dc-1"},
                                     "hosts": [{
                                              'name': "10.1.221.222",
                                              'vms': 4
                                              }]},
                       "name": "cluster-1",
                       "type": "esxcluster",
                       "state": "activated",
                       "id": fake_id1,
                       "hosts": {"host-1": {"name": "10.1.1.1"}}
                       }

cluster_moid1 = "domain-c1"
vc_data_remove = {'cluster': 'cluster-1',
                  'cluster_moid': cluster_moid1,
                  'datacenter': 'dc-1'}

get_all_res = [res_mgr_data1, res_mgr_data2]

provision_data = {"type": "hlinux"}
provision_data_hlinux = {"type": "hlinux",
                         "boot_from_san": True,
                         "os_version": "7.2"}
provision_data_rhel = {"type": "rhel",
                       "boot_from_san": True,
                       "os_version": "7.2"}

baremetal_resource_data = {"id": "baremetal-node",
                           "type": "baremetal",
                           "state": "imported",
                           "ip_address": "10.10.10.10",
                           "username": "user",
                           "password": "password",
                           "meta_data": [
                                          {"key": "ilo_ip",
                                           "value": "10.1.1.0"},
                                          {"key": "mac_addr",
                                           "value": "ma:ya:nk"}
                                          ],
                           "nic_mappings": "4-port"}

rhel_resource_data = {"id": "rhel-node",
                           "type": "rhel",
                           "state": "imported",
                           "ip_address": "10.10.10.10",
                           "password": "password",
                           "meta_data": [
                                          {"key": "ilo_ip",
                                           "value": "10.1.1.0"},
                                          {"key": "mac_addr",
                                           "value": "ma:ya:nk"}
                                          ],
                           "os_version": "rhel72",
                           "boot_from_san": "yes",
                           "property": ["new-random-prop=1", "custom1=2"],
                           "hostname": "rhelcomp",
                           "fcoe_interfaces": ["f2:0b:0a:30:00:70",
                                               "f2:0b:0a:30:00:71"]
                    }

kvm_resource_data = {"id": "hlinuxnode",
                           "type": "hlinux",
                           "state": "provisioned",
                           "ip_address": "10.10.10.10",
                           "password": "password",
                           "meta_data": [
                                          {"key": "ilo_ip",
                                           "value": "10.1.1.0"},
                                          {"key": "mac_addr",
                                           "value": "ma:ya:nk"}
                                          ],
                           "boot_from_san": "yes",
                           "property": ["new-random-prop=1", "custom1=2"]
                    }

deployer_info = {"id": "deployer", "ip-addr": "192.14.50.110",
                 "role": "HLM-ROLE", "server-group": "RACK1"}


networks = [{"name": "CONF-R1", "tagged-vlan": False, "network-group": "CONF",
             "cidr": "12.12.12.0/22", "start-address": "12.12.12.54",
             "end-address": "12.12.12.200", "gateway-ip": "12.12.12.10",
             "addresses": ["192.12.38.10-192.12.39.255"]},
            {"name": "DCM-R1", "tagged-vlan": True, "vlanid": 1,
              "network-group": "DCM", "cidr": "10.1.192.0/18",
              "start-address": "10.1.221.54", "end-address": "10.1.221.70",
              "gateway-ip": "10.1.192.1"},
            {"name": "CLM-R1", "tagged-vlan": True, "vlanid": 1528,
             "network-group": "DCM", "cidr": "10.1.192.0/18",
             "start-address": "10.1.221.54", "end-address": "10.1.221.70",
             "gateway-ip": "10.1.192.1"},
            {"name": "CAN-R1", "tagged-vlan": True, "vlanid": 1540,
             "network-group": "CAN", "cidr": "19.19.0.0/24",
             "start-address": "19.19.0.10", "end-address": "19.19.0.200"},
            {"name": "EXTERNAL-R1", "tagged-vlan": True, "vlanid": 1540,
             "network-group": "EXTERNAL"},
            {"name": "VxLAN-R1", "tagged-vlan": True, "vlanid": 1541,
             "network-group": "VxLAN", "cidr": "189.200.0.0/24",
             "start-address": "189.200.0.10", "end-address": "189.200.0.200",
             "gateway-ip": "189.200.0.1"},
            {"name": "VLAN1-R1", "tagged-vlan": True, "vlanid": 1541,
             "network-group": "VLAN1", "cidr": "189.200.0.0/24",
             "start-address": "189.200.0.10", "end-address": "189.200.0.200",
             "gateway-ip": "189.200.0.1"},
            {"name": "VLAN2-R1", "tagged-vlan": True, "vlanid": 1541,
             "network-group": "VLAN2", "cidr": "189.200.0.0/24",
             "start-address": "189.200.0.10", "end-address": "189.200.0.200",
             "gateway-ip": "189.200.0.1"}, ]


network_groups = [{"name": "CONF", "hostname-suffix": "conf",
                   "component-endpoints": ["lifecycle-manager",
                                        "lifecycle-manager-target"]},
                  {"name": "DCM", "hostname": True,
                   "hostname-suffix": "dcm", "routes": ["default"],
                   "component-endpoints": ["default"],
                   "load-balancers": [{"provider": " ip-cluster",
                                       "name": "dcm-loadbalancer",
                                       "components": ["default"],
                                       "roles": ["internal", "admin"]}],
                   "tags": ["neutron.ovsvapp.management_if"]},
                  {"name": "CAN", "hostname-suffix": "can",
                   "load-balancers": [{"provider": "ip-cluster",
                                       "name": "can-loadbalancer",
                                       "components": ["default"],
                                       "roles": ["public"]}]},
                  {"name": "EXTERNAL",
                   "tags": ["neutron.l3_agent.external_network_bridge"]},
                  {"name": "VxLAN", "tags": [{"neutron.networks.vxlan":
                                 {"tenant-vxlan-id-range": "10000:20000"}}]},
                  {"name": "VLAN1", "tags": [{"neutron.networks.vlan":
                                 {"provider-physical-network": "vlan",
                                  "tenant-vlan-id-range": "1077:1081"}}]},
                  {"name": "VLAN2", "tags": [{"neutron.networks.vlan":
                                {"tenant-vlan-id-range": "10000:20000"}}]},
                  {"name": "iSCSI", "hostname-suffix": "iscsi"},
                  {"name": "TRUNK", "hostname-suffix": "trunk",
                   "tags": ["neutron.ovsvapp.sec_bridge_if"]}]


ovsvapp_interfaces = {"name": "OVSVAPP-INTERFACES",
                      "network-interfaces": [
                        {"name": "eth0",
                         "device": {"name": "eth0"},
                         "forced-network-groups": ["CONF"]},
                        {"name": "eth1",
                         "device": {"name": "eth1"},
                         "network-groups": ["DCM"]},
                        {"name": "eth2",
                         "device": {"name": "eth2"},
                         "network-groups": ["TRUNK"]},
                        {"name": "eth3",
                         "device": {"name": "eth3"},
                         "network-groups": ["VLAN1"]}]}

pass_through = {'pass_through':
                {"pass-through":
                 {"servers": [
                              {"data":
                               {"vmware":
                                {"vcenter_username": "fv",
                                 "vcenter_ip": "10.1.214.12",
                                 "vcenter_id":
                                 "62C354B5-0F1F-423D-A932-441FF000F083",
                                 "vcenter_cluster": "Flash",
                                 "cert_check": False,
                                 "vcenter_port": "443"
                                 }
                                },
                               "id": "2be5aca70f237f56260116a4a67fa6e88ffc1db8"
                               }
                              ]
                  }
                 },
                'servers':
                {'servers': [
                             {'ip-addr': '12.12.15.6',
                              'server-group': 'RACK1',
                              'role': 'ESX-COMPUTE-ROLE',
                              'id':
                              '2be5aca70f237f56260116a4a67fa6e88ffc1db8'
                              }
                             ]
                 }
                }

exp_inp_nova = {
    "expandedInputModel": {
        "internal": {
            "control-planes": {
                control_plane_name: {
                    "advertises": {
                        "nova-api": {
                            "internal": {
                                "url": "http://10.10.10.10:8774/v2/"
                                "tenant_id/os-services/1234"
                            }
                        }
                    }
                }
            }
        }
    }
}

exp_inp_nova_neutron = {
    "expandedInputModel": {
        "internal": {
            "control-planes": {
                control_plane_name: {
                    "advertises": {
                        "nova-api": {
                            "internal": {
                                "url": "My_nova_url"
                            }
                        },
                        "neutron-server": {
                            "internal": {
                                "url": "http://10.10.10.10:8774/v2/tenant_id"
                                "/os-services/1234"
                            }
                        }
                    }
                }
            }
        }
    }
}

hyp = [{
    "id": 2,
    "service": {},
    "hypervisor_hostname": "domain-0.cluster-0"
}, {
    "id": 1,
    "service": {},
    "hypervisor_hostname": "hypervisor_hostname",
    "running_vms": 1
}, {
    "service": {
        "host": "hypervisor_hostname",
        "id": 2
    }
}]

hyp1 = [{
    "id": 2,
    "service": {},
    "hypervisor_hostname": "domain-0.cluster-0"
}, {
    "id": 1,
    "service": {},
    "hypervisor_hostname": "hypervisor_hostname",
    "running_vms": 1
}]

agents = [
                            {"binary": "hpvcn-neutron-agent",
                             "alive": True,
                             "id": "1234",
                             "host": "hypervisor_hostname",
                             "agent_type": "HP VCN L2 Agent",
                             "configurations":
                             {"esx_host_name": u"10.1.214.177"}
                             },
                           {"binary": "hpvcn-neutron-agent",
                             "alive": True,
                             "id": u"5678",
                             "host": "ovsvapp-10-1-214-178",
                             "agent_type": "HP VCN L2 Agent",
                             "configurations":
                             {"esx_host_name": u"10.1.214.178"}
                             },
                            ]


def get_res_fake_inv(x, y):
    return {
            "datacenter": {
            "moid": "datacenter-2",
            "name": "dc"},
            "hosts": []
            }


FAKE_PASS_THRU = json.loads("""{"global":
{"install_env":"cs","install_version":"10",
"thirdparty_folder":"/home/stack/stage/thirdparty",
"lib_mysql_java_file_name":"libmysql-java_5.1.32-1_all.deb",
"qpress_file_name":"","ovftool_installer":
"VMware-ovftool-4.1.0-2459827-lin.x86_64.bundle","oo_admin_password":
"unset","is_foundation_installed":true,"hyperv_cloud":true,"hpecs":
{"networks":[{"members":[{"cidr":"192.19.90.0/24","addresses":
["192.19.90.232-192.19.90.253"],"allocations":{"ace":
["192.19.90.251","192.19.90.251"],"esx":["192.19.90.252","192.19.90.253"]}}],
"name":"CONF","types":["u'hlm'"]}]},"esx_cloud":true},"servers":[{"data":
{"vmware":{"vcenter_username":"Administrator@vsphere.local",
"vcenter_ip":"10.1.213.200","vcenter_id":
"20af7146-5363-41e5-81a1-fb75e151b614","vcenter_cluster":"MAT_KVM",
"cert_check":false,"vcenter_port":"443"}},"id":
"b4d8bed9a519bd8dd7586ffa3f8de56e3799008c"},
{"data":{"vmware":{"vcenter_username":"Administrator@vsphere.local",
"cluster_dvs_mapping":"MAT_DT/host/MAT_KVM:TRUNK-DVS-bh-MAT_KVM","vcenter_ip":
"10.1.213.200","esx_hostname":"10.1.212.104",
"vcenter_id":"20af7146-5363-41e5-81a1-fb75e151b614",
"vcenter_cluster":"MAT_KVM","cert_check":false,"vcenter_port":"443"}},
"id":"9c00feb76f993537f233a8518b69357445b06596"}]}""")


FAKE_INPUT_MODEL = json.loads('{"name":"test-model","fileInfo":{"files":'
                              '["data/control_plane_esx.yml"],"sections":'
                              '{"product":["data/control_plane_esx.yml"]},'
                              '"fileSectionMap":{"data/control_plane_esx.yml":'
                              '["product",{"control-planes":["cp-esx"],'
                              '"keyField":"name","type":"array"}]}},'
                              '"inputModel":{"control-planes":[]}}')

EMPTY_PASS_THRU = json.loads('{"name":"test-model","fileInfo":{"files":'
                             '["data/control_plane_esx.yml",'
                             '"data/pass_through.yml"],"sections":{"product":'
                             '["data/control_plane_esx.yml",'
                             '"data/pass_through.yml"],"pass-through":'
                             '["data/pass_through.yml"]},"fileSectionMap":'
                             '{"data/control_plane_esx.yml":["product",'
                             '{"control-planes":["cp-esx"],"keyField":"name",'
                             '"type":"array"}],"data/pass_through.yml":'
                             '["product","pass-through"]}},"inputModel":'
                             '{"control-planes":[],"pass-through":'
                             '{"servers":[], "global": {}}}}')


class FakeContext(object):

    def __init__(self):
        self.auth_token = "509ba3bce14444079985c5ecf21760dc"


fake_control_plance = [{"resources":
                            [{"allocation-policy": "any",
                              "name": "kvm-compute-nb2d",
                              "service-components": ["ntp-client",
                                                     "nova-compute",
                                                     "nova-compute-kvm",
                                                     "neutron-l3-agent",
                                                     "neutron-metadata-agent",
                                                 "neutron-openvswitch-agent",
                                                     "neutron-lbaasv2-agent"],
                              "resource-prefix": "kvm-comp-nb2d",
                              "min-count": 0, "server-role":
                                  "KVM-COMPUTE-ROLE-NO-BOND-2-DISKS"},
                             {"allocation-policy": "any",
                              "name": "kvm-compute-nb1d",
                              "service-components": ["ntp-client",
                                                     "nova-compute",
                                                     "nova-compute-kvm",
                                                     "neutron-l3-agent",
                                                     "neutron-metadata-agent",
                                                 "neutron-openvswitch-agent",
                                                     "neutron-lbaasv2-agent"],
                              "resource-prefix": "kvm-comp-nb1d",
                              "min-count": 0,
                          "server-role": "KVM-COMPUTE-ROLE-NO-BOND-1-DISK"},
                             {"allocation-policy": "any",
                              "name": "kvm-compute-nb2sd",
                              "service-components": ["ntp-client",
                                                     "nova-compute",
                                                     "nova-compute-kvm",
                                                     "neutron-l3-agent",
                                                     "neutron-metadata-agent",
                                                 "neutron-openvswitch-agent",
                                                     "neutron-lbaasv2-agent"],
                              "resource-prefix": "kvm-comp-nb2sd",
                              "min-count": 0,
                      "server-role": "KVM-COMPUTE-ROLE-NO-BOND-2SAN-DISKS"},
                             {"allocation-policy": "any",
                              "name": "hyperv-compute-nobond",
                              "service-components": ["nova-compute-hyperv",
                                                     "neutron-hyperv-agent"],
                              "resource-prefix": "hyperv-comp-nobond",
                      "min-count": 0,
                              "server-role": "HYPERV-COMPUTE-ROLE-NO-BOND"},
                             {"allocation-policy": "any",
                              "name": "hyperv-compute-bond",
                              "service-components": ["nova-compute-hyperv",
                     "neutron-hyperv-agent"],
                              "resource-prefix": "hyperv-comp-bond",
                              "min-count": 0,
                              "server-role": "HYPERV-COMPUTE-ROLE-BOND"}]}]

fake_server_groups = [{"server-groups": ["AZ1", "AZ2", "AZ3"],
                       "name": "CLOUD", "networks":
                           ["VLAN-R1", "EXTERNAL-R1", "CAN-R1", "DCM-R1",
                            "CLM-R1", "CONF-R1", "TRUNK-NET"]},
                      {"server-groups": ["RACK1"], "name": "AZ1"},
                      {"server-groups": ["RACK2"], "name": "AZ2"},
                      {"server-groups": ["RACK3"], "name": "AZ3"},
                      {"name": "RACK1"}, {"name": "RACK2"},
                      {"name": "RACK3"}]


class FakeVCSession(object):
    """it is a fake session for pyvmomi objects
    """
    def __init__(self):
        mock_Si = mock.MagicMock()
        mock_Si.content = mock.Mock()
        mock_Si.content.ovfManager = mock.Mock()
        mock_Si.content.rootFolder = mock.Mock()
        mock_Si.content.rootFolder.find_by_name = self._find_by_name
        self.si = mock_Si
        self.content = mock_Si.content
        self.si.RetrieveContent = mock.Mock

    def _find_by_name(self, name):
        if name == "hlm-shell-ova":
            return mock.Mock()

    def __getitem__(self, attr):
        return getattr(self, attr)

    def get(self, attr):
        return getattr(self, attr)

    def __setitem__(self, attr, value):
        pass
