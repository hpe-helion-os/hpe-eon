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

status_codes = {}
status_codes[100] = "'vcenter_username' has not been provided"
status_codes[101] = "'vcenter_password' has not been provided"
status_codes[102] = "'vcenter_https_port' has not been provided"
status_codes[103] = "'datacenter' name has not been provided"
status_codes[104] = "'clusters' names have not been provided"

status_codes[105] = "'tenant_network_type' has not been provided"
status_codes[106] = "'mgmt_dvs_name' has not been provided"
status_codes[107] = "'trunk_dvs_name' has not been provided"
status_codes[108] = "'uplink_dvs name' has not been provided"
status_codes[109] = "'data_pg_name' has not been provided"
status_codes[110] = "'trunk_pg_name'has not been provided"
status_codes[111] = "'mgmt_pg_name'has not been provided"
status_codes[112] = "'deployer_pg_name'has not been provided"
status_codes[113] = "'mgmt_nic_name' for Mgmt DVS has not been provided"
status_codes[114] = "OVSvApp Template/Appliance name has not been provided"
status_codes[115] = "'ssh_key' has not been provided"
status_codes[116] = "'json_file' path has not been provided"
status_codes[117] = "'data_nic_name' for Data DVS has not been provided"
status_codes[118] = ("Either interface order has not been provided or is "
                     "invalid")
status_codes[119] = "'deployer_node_ip' has not been provided"

status_codes[200] = "Connected to vCenter server"
status_codes[201] = "Successfully created DVS"
status_codes[202] = "DVS already exists"
status_codes[203] = "OVSvApp has been created and configured successfully"
status_codes[204] = "Successfully disabled HA & DRS for OVSvApp VM"
status_codes[205] = "Successfully deleted OVSvApp"
status_codes[206] = "Successfully updated OVSvApp"
status_codes[207] = "Successfully deleted DVS/portgroup"

status_codes[300] = "Invalid vCenter host has been provided"
status_codes[301] = "Invalid vCenter https port has been provided"
status_codes[302] = "Invalid 'mgmt_vlan' has been provided"
status_codes[303] = "Malformed VLAN in vlan_range"
status_codes[304] = "Invalid VLAN in vlan_range"
status_codes[305] = "Invalid mgmt ips/range have been provided"
status_codes[306] = "Invalid mgmt gateway IP"
status_codes[307] = "Invalid mgmt subnet mask"
status_codes[308] = ("Corrupted template! Please remove all vnics or PCI "
                     "devices from template")
status_codes[309] = ("Unsupported ESXi Version ! Minimum supported ESXi "
                     "version is 5.0")
status_codes[310] = "ESXi host is in invalid power state"
status_codes[311] = "ESXi host already contains OVSvApp"
status_codes[312] = ("IP range contains less number of IPs than the number of "
                     "ESXi hosts")
status_codes[313] = "Either ESXi host or the OVSvApp is in invalid state"
status_codes[314] = ("Provided physical nic/nics are either used/busy or they "
                     "don't exist. Couldn't attach the host in DVS.")
status_codes[315] = "Invalid DNS servers"
status_codes[316] = "Active nics should be present in Mgmt nics or Data nics"
status_codes[317] = "Load balancing value should be between 1 and 4"
status_codes[318] = "Network failover detection value should be either 1 or 2"
status_codes[319] = "Beacon probing cannot be used with IP-hash load balancing"
status_codes[320] = "Invalid Routes"
status_codes[321] = "ESXi host is not in maintenance mode"
status_codes[322] = "ESXi host is not attached with any shared datastore"
status_codes[323] = "Duplicate Static IP for mgmt interface"
status_codes[324] = "Invalid tenant network type ! Only vlan is supported."
status_codes[325] = "Invalid deployer ips/range have been provided"
status_codes[326] = "Invalid deployer gateway IP"
status_codes[327] = "Invalid deployer subnet mask"

status_codes[400] = "Couldn't find any Datacenter with the provided name"
status_codes[401] = "Couldn't find any cluster with the provided name"
status_codes[402] = "Couldn't find the OVSvApp Template/Appliance"
status_codes[403] = "Couldn't find the DVS with the provided name"
status_codes[404] = ("Couldn't find any valid ESXi host to continue "
                     "the installation")

status_codes[500] = ("Cannot complete login due to an incorrect user name or "
                     "password.")
status_codes[501] = "Could not connect to the specified vCenter server."
status_codes[502] = "Error occurred while cloning OVSvApp"
status_codes[503] = ("Either the host is not added to any one of the DVS or "
                     "the DVS/portgroup doesn't exist")
status_codes[504] = ("Timed out while waiting for VMware Tools to be "
                     "ready. This means either VMware Tools is not "
                     "installed on the OVSvApp appliance or the VM "
                     "took more than 5 mins to boot up")
status_codes[505] = "Couldn't send the SSH key inside OVSvApp VM"
status_codes[506] = ("OVSvApp autoprep script to customize the VM could not "
                     "be sent. Customization of the VM has failed")

status_codes[507] = ("Couldn't create DVS/DVPortgroup because of duplicate "
                     "names")
status_codes[508] = "Couldn't create DVS/DVPortgroup"
status_codes[509] = "Couldn't delete DVS/portgroup. The resource is in use."
status_codes[510] = "Couldn't take snapshot of the OVSvApp template/appliance"


def get_status(code, **kwargs):
    msg = {'status_code': code, 'status_message': status_codes.get(code)}
    if kwargs:
        message = dict(msg, **kwargs)
        return message
    return msg
