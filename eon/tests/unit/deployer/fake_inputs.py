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

data = {
    "switches": [
        {
            "type": "dvSwitch",
            "name": "MGMT-DVS",
            "physical_nics": "vmnic1",
            "mtu": "1500"
        },

        {
            "type": "dvSwitch",
            "name": "TRUNK-DVS",
            "physical_nics": "",
            "mtu": "1500"
        }
    ],

    "portGroups": [
        {
            "name": "ESX-CONF",
            "vlan": "33",
            "vlan_type": "trunk",
            "switchName": "MGMT-DVS",
            "nic_teaming": {
                "network_failover_detection": "1",
                "notify_switches": "yes",
                "load_balancing": "1",
                "active_nics": "vmnic1"
            }
        },

        {
            "name": "MGMT",
            "vlan": "",
            "vlan_type": "none",
            "switchName": "MGMT-DVS",
            "nic_teaming": {
                "network_failover_detection": "1",
                "notify_switches": "yes",
                "load_balancing": "1",
                "active_nics": "vmnic1"
            },
            "cloud_network_type": "vlan"
        },

        {
            "name": "TRUNK",
            "vlan": "1-4094",
            "vlan_type": "trunk",
            "switchName": "TRUNK-DVS"
        }
    ],

    "vm_config": [
        {
            "server_role": "ESX-COMPUTE-ROLE",
            "template_name": "hlm-shell-vm",
            "template_location": "fake_location",
            "cpu": "4",
            "memory_in_mb": "4096",
            "nics": [
                {
                    "device": "eth0",
                    "portGroup": "ESX-CONF",
                    "type": "vmxnet3",
                    "pci_id": ""
                },
                {
                    "device": "eth1",
                    "portGroup": "MGMT",
                    "type": "vmxnet3",
                    "pci_id": ""
                }
            ]
        },

        {
            "server_role": "OVSVAPP-ROLE",
            "template_name": "hlm-shell-vm",
            "template_location": "fake_location",
            "cpu": "4",
            "memory_in_mb": "4096",
            "nics": [
                {
                    "device": "eth0",
                    "portGroup": "ESX-CONF",
                    "type": "vmxnet3",
                    "pci_id": ""
                },
                {
                    "device": "eth1",
                    "portGroup": "MGMT",
                    "type": "vmxnet3",
                    "pci_id": ""
                },
                {
                    "device": "eth2",
                    "portGroup": "TRUNK",
                    "type": "vmxnet3",
                    "pci_id": ""
                }
            ]
        }
    ],

    "esx_conf_net": {
        "portGroup": "ESX-CONF",
        "cidr": "10.21.18.0/23",
        "start_ip": "",
        "end_ip": "",
        "gateway": "10.21.18.1"
    },

    "lifecycle_manager": {
        "ip_address": "10.20.16.2",
        "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EA stack@company.org",
        "user": "stack"
    },

    "vcenter_configuration": {
        'username': 'root',
        'datacenter': 'DC-Fake',
        'ip_address': '10.10.10.11',
        'port': 443,
        'cluster': 'Cluster1',
        'password': 'password',
        'cluster_moid': 'domain-c01'
    }
}


fake_clusters = {
    'resourcePool': 'vim.ResourcePool:resgroup-8',
    'name': 'Cluster1',
    'host': [
        'vim.HostSystem:host-10',
        'vim.HostSystem:host-34'
    ],
    'mo_id': 'domain-c7',
    'obj': 'vim.ClusterComputeResource:domain-c7',
    'datastore': [
        'vim.Datastore:datastore-30',
        'vim.Datastore:datastore-35'
    ]
}

fake_datacenter = {
    'name': 'Datacenter1',
    'vmFolder': 'group-v01',
    'hostFolder': [{
        'host2': 'cluster2',
        'host1': 'cluster1'
    }],
    'networkFolder': 'group-n01'}


class MOB:

    class content():

        class rootFolder:
            pass

        class propertyCollector:

            class RetrieveContents:
                pass

        class viewManager:

            class CreateContainerView:

                def __init__(self, obj, obj_type, val):
                    self.obj = obj
                    self.obj_type = obj_type
                    self.val = val

                class Name:
                    name = 'fake_name'
                    _moId = 'fake_moid'

                view = [Name]

    def RetrieveContent(self):
        pass


session = {'content': MOB.content, 'si': 'session_intance'}
