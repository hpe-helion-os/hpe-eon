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

prop_spec_map = {"Datacenter": ["name",
                                "hostFolder",
                                "networkFolder"],
                 "Folder": ["name",
                            "childEntity"],
                 "ClusterComputeResource": ["name",
                                            "host",
                                            "parent",
                                            "datastore",
                                            "configurationEx",
                                            "summary.totalMemory",
                                            ],
                 "HostSystem": ["name", "parent", "runtime.connectionState",
                                "vm"],
                 "Datastore": ["name",
                               "host",
                               "summary.capacity",
                               "summary.freeSpace",
                               "summary.accessible"],
                 }

VCENTER_RECONNECT_INTERVAL = 10

ESX_PROXY_NAME = 'computeproxy'
NETWORK_DRIVER = 'network_driver'

NET_PROPS = "network_properties"
DEFAULT_COMPUTE_PROXY_ROLE_NAME = 'ESX-COMPUTE-ROLE'
DEFAULT_NETWORK_DRIVER_ROLE_NAME = 'OVSVAPP-ROLE'

CLUSTER_DVS_MAPPING = "cluster_dvs_mapping"
ESX_HOST_NAME = "esx_hostname"
CLUSTER_MOID = "cluster_moid"

HLM_VERSION = "4.0"
CPU = "4"
MEMORY_IN_MB = "4096"
DVSWITCH = "dvSwitch"
TRUNK_DVS = "TRUNK-DVS"
DEFAULT_MTU = "1500"
NETWORK_TYPE_VLAN = "neutron.networks.vlan"
TENANT_VLAN_RANGE = "tenant-vlan-id-range"
NETWORK_TYPE_VXLAN = "neutron.networks.vxlan"
HLINUX_OVA_TEMPLATE_NAME = "hlm-shell-vm"
UPLOAD_TO_CLUSTER = "upload_to_cluster"
OVSVAPP_INTERFACES = "OVSVAPP-INTERFACES"
ESX_COMPUTE_INTERFACES = "ESX-COMPUTE-INTERFACES"
ESX_COMPUTE_ROLE = "ESX-COMPUTE-ROLE"
OVSVAPP_ROLE = "OVSVAPP-ROLE"
SSH_KEY_FILE = "/opt/stack/service/eon-conductor/etc/eon/hlm_ssh_key"
CONF_NETWORK_TYPE = "CONF"
CLM_NETWORK_TYPE = "CLM"
VLAN = "vlan"
VXLAN = "vxlan"
MAX_IPADDR = 380
HPECS = "hpecs"
OVSVAPP_NETWORK_DRIVER = "ovsvapp"
NOOP_NETWORK_DRIVER = "noop"
