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

EON_RESOURCE_MGR_TYPES = ['vcenter']
EON_RESOURCE_MGR_TYPE_VCENTER = "vcenter"
EON_RESOURCE_TYPE_ESX_CLUSTER = "esxcluster"
CLUSTER_MOID = "cluster_moid"
EON_RESOURCE_TYPE_ESX_CLUSTER_NETWORK = "esxcluster_network"
EON_RESOURCE_TYPE_ESX_CLUSTER_COMPUTE = "esxcluster_compute"

EON_RESOURCE_IP_ADDRESS = "ip_address"
EON_RESOURCE_USERNAME = "username"
EON_RESOURCE_PASSWORD = "password"
EON_RESOURCE_NAME = "name"
EON_RESOURCE_PORT = "port"
EON_RESOURCE_TYPE = "type"
EON_RESOURCE_ID = "id"
EON_RESOURCE_META_KEY = 'meta_data'
EON_RESOURCE_STATE = 'state'
EON_RESOURCE_MGR_ID = "resource_mgr_id"

EON_RESOURCE_MANAGER_STATE_REGISTERED = "registered"
EON_RESOURCE_MANAGER_STATE_UPDATING = "updating"
RESOURCE_MGR_STATE_KEY = EON_RESOURCE_STATE

EON_RESOURCE_STATE_IMPORTED = "imported"
EON_RESOURCE_STATE_PROVISIONING = "provisioning"
EON_RESOURCE_STATE_PROVISIONED = "provisioned"
EON_RESOURCE_STATE_ACTIVATING = "activating"
EON_RESOURCE_STATE_ACTIVATED = "activated"
EON_RESOURCE_STATE_REMOVING = "removing"
EON_RESOURCE_STATE_REMOVED = "removed"
RESOURCE_STATE_PROVISON_INITIATED = "provision-initiated"
RESOURCE_STATE_REMOVAL_INITIATED = "cleanup-initiated"
RESOURCE_STATE_ACTIVATION_INITIATED = "activation-initiated"
EON_RESOURCE_STATE_DEACTIVATING = "deactivating"
RESOURCE_STATE_HOST_COMMISSIONING = "host-commissioning"
RESOURCE_STATE_HOST_COMMISSION_INITIATED = "host-commission-initiated"
DECRYPT_LOOK_UP_STR = "{{ lookup('pipe','/usr/bin/eon-encrypt -d %s') }}"

ACTIVATION_STATE_MAPPING = {EON_RESOURCE_STATE_IMPORTED:
                            RESOURCE_STATE_PROVISON_INITIATED,
                            EON_RESOURCE_STATE_PROVISIONED:
                            RESOURCE_STATE_ACTIVATION_INITIATED
                            }
DEACTIVATION_STATE_MAPPING = {EON_RESOURCE_STATE_PROVISIONED:
                              RESOURCE_STATE_REMOVAL_INITIATED,
                              EON_RESOURCE_STATE_ACTIVATED:
                              EON_RESOURCE_STATE_DEACTIVATING
                              }
HOST_COMMISSION_MAPPING = {EON_RESOURCE_STATE_ACTIVATED:
                           RESOURCE_STATE_HOST_COMMISSION_INITIATED
                           }
EON_RESOURCE_RESPONSE_ATTRS_FROM_DB = \
    (EON_RESOURCE_NAME, EON_RESOURCE_USERNAME, EON_RESOURCE_PASSWORD,
     EON_RESOURCE_IP_ADDRESS, EON_RESOURCE_PORT, EON_RESOURCE_ID,
     EON_RESOURCE_TYPE, EON_RESOURCE_MGR_ID,
     EON_RESOURCE_STATE)

RSRC_MGR_INFO = "resource_manager_info"
SUPPORTED_UPDATE_FIELDS = [EON_RESOURCE_IP_ADDRESS, EON_RESOURCE_USERNAME,
                           EON_RESOURCE_PASSWORD, EON_RESOURCE_PORT]
EXPECTED_STATE = ['activated', 'provisioning', 'provisioned',
                  'activating']

EXPECTED_STATE_ACTIVATED = ["activated"]
INPUT_MODEL_ADD = "add"
INPUT_MODEL_REMOVE = "remove"
INPUT_MODEL_UPDATE = "update"

EON_RESOURCE_MANAGER = "resource_manager"
EON_RESOURCE = "resource"

# Constants for baremetal
EON_RESOURCE_TYPE_BAREMETAL = "baremetal"
EON_RESOURCE_MAC_ADDR = 'mac_addr'
EON_RESOURCE_ILO_IP = 'ilo_ip'
EON_RESOURCE_ILO_USER = 'ilo_user'
EON_RESOURCE_ILO_PASSWORD = 'ilo_password'
EON_RESOURCE_ANSIBLE_OPTIONS = 'ansible_options'

FORCED_KEY = 'forced'

EON_RESOURCE_TYPE_HLINUX = "hlinux"
EON_RESOURCE_TYPE_KVM = "kvm"
EON_RESOURCE_TYPE_HYPERV = "hyperv"
EON_RESOURCE_TYPE_RHEL = "rhel"

# provision payload map
PROVISION_PAYLOAD = [EON_RESOURCE_ID, EON_RESOURCE_IP_ADDRESS]
PROVISION_PAYLOAD_METADATA = [EON_RESOURCE_MAC_ADDR,
                              EON_RESOURCE_ILO_IP,
                              EON_RESOURCE_ILO_USER,
                              EON_RESOURCE_ILO_PASSWORD]

EXPECTED_STATES_ACTIVATION = {EON_RESOURCE_TYPE_ESX_CLUSTER: [
                                EON_RESOURCE_STATE_IMPORTED,
                                EON_RESOURCE_STATE_PROVISIONED
                                ],
                              EON_RESOURCE_TYPE_HYPERV:
                                [EON_RESOURCE_STATE_PROVISIONED],
                              EON_RESOURCE_TYPE_HLINUX:
                                [EON_RESOURCE_STATE_PROVISIONED],
                              EON_RESOURCE_TYPE_RHEL:
                                [EON_RESOURCE_STATE_PROVISIONED],
                              }
EXPECTED_STATES_DEACTIVATION = {EON_RESOURCE_TYPE_ESX_CLUSTER: [
                                EON_RESOURCE_STATE_PROVISIONED,
                                EON_RESOURCE_STATE_ACTIVATED
                                ],
                              EON_RESOURCE_TYPE_HYPERV:
                                [EON_RESOURCE_STATE_ACTIVATED],
                              EON_RESOURCE_TYPE_HLINUX:
                                [EON_RESOURCE_STATE_ACTIVATED],
                              EON_RESOURCE_TYPE_RHEL:
                                [EON_RESOURCE_STATE_ACTIVATED],
                              }
ROLLBACK_STATE_ACTIVATION = {EON_RESOURCE_TYPE_ESX_CLUSTER:
                                EON_RESOURCE_STATE_IMPORTED,
                            EON_RESOURCE_TYPE_HYPERV:
                                EON_RESOURCE_STATE_PROVISIONED,
                            EON_RESOURCE_TYPE_HLINUX:
                                EON_RESOURCE_STATE_PROVISIONED,
                            EON_RESOURCE_TYPE_RHEL:
                                EON_RESOURCE_STATE_PROVISIONED,
                              }
RUN_PLAYBOOK = "run_playbook"
RUN_WIPE_DISKS = "run_wipe_disks"
SKIP_DISK_CONFIG = "skip_disk_config"
INPUT_MODEL = "input_model"
HLM_PROPERTIES = "hlm_properties"
NETWORK_PROPERTIES = "network_properties"
HYPERVISOR_ID = "hypervisor_id"
DB_RESOURCE_PROP = [HLM_PROPERTIES,
                    NETWORK_PROPERTIES,
                    HYPERVISOR_ID]

HYPERV_CLOUD = "hyperv_cloud"
ESX_CLOUD = "esx_cloud"

# resource activation map
NIC_MAPPINGS = "nic_mappings"
SERVER_ROLE = "server_role"
SERVER_GROUP = "server_group"
HOSTNAME = "hostname"
FCOE_INTERFACES = "fcoe_interfaces"
ACTIVATE_PAYLOAD = [NIC_MAPPINGS, SERVER_ROLE, SERVER_GROUP, HOSTNAME,
                    FCOE_INTERFACES]
BOOT_FROM_SAN = "boot_from_san"

HLM_PAYLOAD_MAP = {EON_RESOURCE_ID: "id",
               EON_RESOURCE_IP_ADDRESS: "ip-addr",
               NIC_MAPPINGS: 'nic-mapping',
               SERVER_ROLE: 'role',
               SERVER_GROUP: 'server-group',
               EON_RESOURCE_MAC_ADDR: 'mac-addr',
               EON_RESOURCE_ILO_IP: 'ilo-ip',
               EON_RESOURCE_ILO_USER: 'ilo-user',
               EON_RESOURCE_ILO_PASSWORD: 'ilo-password',
               EON_RESOURCE_ANSIBLE_OPTIONS: 'ansible-options',
               BOOT_FROM_SAN: 'boot-from-san',
               HOSTNAME: 'hostname',
               FCOE_INTERFACES: 'fcoe-interfaces'
               }

# constant for cobbler profile
VERSION = "os_version"
COBBLER_PROFILE = "distro-id"
RHEL72 = "rhel72-x86_64"
COBBLER_PROFILE_MAP = {"rhel72": RHEL72}

SUBSCRIPTION_REPO_PATH = "/etc/yum/pluginconf.d/subscription-manager.conf"
CHECK_KERNAL_VERSION = 'uname -r'
CHECK_KERNAL_VERSION_PATTERN_RHEL7 = "^3.10.*x86_64$"
DISABLE_PASSWD_AUTHENTICATION = ("""/usr/bin/sudo sed -i """ +
                                 """"/PasswordAuthentication yes""" +
                                 """/c\PasswordAuthentication no" """ +
                                 """/etc/ssh/sshd_config""")
RESTART_SSH = " sudo systemctl restart sshd"
MKDIR_MARKER_PARENT_DIR = "sudo mkdir -p /etc/hos/"
CREATE_SKIP_DISK_CONFIG_MARKER = "sudo touch /etc/hos/skip_disk_config"
DELETE_SKIP_DISK_CONFIG_MARKER = "sudo rm -f /etc/hos/skip_disk_config"
OSCONFIG_RAN_MARKER = "/etc/hos/osconfig-ran"
DEFAULT_YUM_TIMEOUT_SECS = 5 * 60
ACTIVATION = "activation"
DEACTIVATION = "deactivation"
NOVA_HYPERVISOR_LIST_TIMEOUT = 600
CHECK_L2AGENT_TIMEOUT_PER_HOST = 180
NEUTRON_AGENT_TYPE = {
                      "kvm": "Open vSwitch agent",
                      "hyperv": "HyperV agent"}
HYPERV_ANSIBLE_OPTIONS = "ansible_ssh_user=%s" \
                         " ansible_ssh_pass=\"{{ lookup('pipe'," \
                         " '/usr/bin/eon-encrypt -d %s ') }}\"" \
                         " ansible_ssh_port=%s" \
                         " ansible_connection=winrm" \
                         " ansible_winrm_server_cert_validation=ignore"
HYPERV_DEFAULT_PORT = "5986"
HYPERV_DEFAULT_NONSECURED_PORT = "5985"
PS_SCRIPT_TO_GET_HOSTNAME = '''Function GetHostname {
    [system.environment]::MachineName
}
GetHostname
'''

PS_SCRIPT_TO_CHK_OS = '''$Version = [System.Environment]::OSVersion.Version; (
 $Version.Major -eq 6 -and ($Version.Minor -le 3 -and $Version.Minor -ge 1))
'''

PS_SCRIPT_TO_CHK_HYPERV_FEATURE = '''$HyperVFeature = (
Get-WindowsOptionalFeature -Online -FeatureName "Microsoft-Hyper-V")
$HyperVFeature.State -eq "Enabled"
'''

PS_SCRIPT_TO_CHECK_VM_COUNT = '''$VmCount = $(get-vm).Count'''

PS_SCRIPT_TO_STREAM_WRITE = """$stream = [System.IO.StreamWriter] `
"%(file_name)s"
$s = @"
"""

PS_SCRIPT_TO_REPLACE_N = """
"@ | %{ $_.Replace("`n","`r`n") }
$stream.WriteLine($s)
$stream.close()"""

PS_SCRIPT_TO_CHECK_TIME_SYNC = """
$logfile = Join-Path -Path $($env:LOCALAPPDATA) -ChildPath `
"\Temp\activation$(get-date -format `"yyyyMMdd_hhmmsstt`").log"

function logInfo($string)
{
   "INFO:"+$string | out-file -Filepath $logfile -append
}

function logError($string)
{
   "ERROR:"+$string | out-file -Filepath $logfile -append
}

Function CheckDateFromAppliance{
  $retval = $false
  logInfo "Checking host date with cloud mangement controller"
  [string]$checkVal = Get-Service w32time | select -ExpandProperty Status
  if ($checkVal -ne "Running") {
    logInfo "Starting service W32Time"
    net start W32Time | Out-Null
    logInfo "Started service W32Time successfully"
  }

  $serverTime = w32tm /stripchart /dataonly /computer:%(ntpserver_fqdn)s `
  /samples:1
  [int]$timeOffset = $serverTime[3].Split(' ')[1].TrimEnd('s')
  if ($timeOffset -ne $null){
    if ($timeOffset -le 60){
      logInfo ("Synchronized host sucessfully with ntp server on cloud",
        "mangement controller")
      $retval = $true
    } else{
      logInfo "Time difference is too great. Configure manually"
    }
  } else{
    logError ("Time Server Error: Time cannot be synchronized. Configure the",
      "server first")
    }
  return $retval
}
CheckDateFromAppliance
"""

PS_SCRIPT_TO_CHECK_CSV = """
$logfile = Join-Path -Path $($env:LOCALAPPDATA) -ChildPath `
"\Temp\activation$(get-date -format `"yyyyMMdd_hhmmsstt`").log"

function logInfo($string)
{
   "INFO:"+$string | out-file -Filepath $logfile -append
}

function logError($string)
{
   "ERROR:"+$string | out-file -Filepath $logfile -append
}
Function CheckCSV{
   logInfo "Checking if host is in a Cluster."
   if ((Get-WindowsFeature "Failover-Clustering").Installed){
   $instance = (Get-VMHost -ComputerName localhost).`
     VirtualHardDiskPath.TrimEnd("\\")
   $csv = (Get-WmiObject -namespace root\mscluster -computername localhost  `
     -Class mscluster_clustersharedvolume).name
   if ($csv -contains $instance){
   logInfo "instance_path $instance is valid Cluster Shared Volume."
   $retval = "Cluster"
   }else{
   logError ("instance_path  $instance  is not valid Cluster Shared Volume.",
     "It must be one of  { $csv }.")
   $retval = $csv
   }
   }else{
   logInfo "Host is not in a Cluster"
   $retval = "Standalone"
   }
   return $retval
}
CheckCSV
"""

CMD_SCRIPT_TO_GET_TEMP_LOC = """
echo %TEMP%
"""
