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

from pyVmomi import vim

# IP catalog file location in eon conductor
IP_CATALOG_FILE = '/opt/stack/service/eon-conductor/etc/eon/ip_catalog.json'
# Prep script name to prep the shell vms
PREP_SCRIPT = 'customize_service_vm.sh'
# Appliance user name
APPLIANCE_USER = 'stack'
# Appliance encoded password
APPLIANCE_PWD = 'c3RhY2s='
# Temporary prep script location inside shell vm
GUEST_CUSTOMIZATION_SCRIPT = "/".join(
    ['/home', APPLIANCE_USER, 'customize_service_vm.sh'])
# Temporary SSH key location inside shell vm
GUEST_SSH_KEY = "/".join(['/home', APPLIANCE_USER, 'ssh_key'])
# VMTools retry count
VM_TOOLS_RETRY_COUNT = 8
# Shell vm network info count
NET_INFO_COUNT = 10
# Delay time while wait for task
TASK_WAIT_DELAY = 5
# OVSvApp key
OVSVAPP_KEY = 'OVSVAPP'
OVSVAPP_NETWORK_DRIVER = 'ovsvapp'
# ESX Compute Proxy key
PROXY_KEY = 'ESX-COMPUTE-PROXY'

NOOP_NETWORK_DRIVER = 'noop'
# VM Props
VM_PROPS = ['name', 'datastore', 'config.annotation',
           'config.hardware.device', 'runtime.host',
           'runtime.powerState', 'guest.ipAddress']

# HOST COMMISIONING FAILURE KEY
HOST_COMM_FAILURE = 'failure'

TYPE_DVS = vim.DistributedVirtualSwitch
TYPE_PG = vim.dvs.DistributedVirtualPortgroup

# Minimum disk space required to provision OVSvApp/Nova Compute Proxy VMs
BYTES = 1024
VM_RAMDISK = 5
MIN_VMDISK_SIZE_GB = 40
MIN_PROVISION_SPACE = (MIN_VMDISK_SIZE_GB + VM_RAMDISK) * BYTES * BYTES * BYTES
