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

import itertools

from netaddr import IPAddress
from netaddr import IPNetwork
from netaddr.core import AddrFormatError

from eon.common import exception
from eon.common import log
from eon.deployer import constants
from eon.deployer import util
from eon.deployer.network.ovsvapp.util import status_messages
from eon.deployer.network.ovsvapp.util import vapp_constants


LOG = log.getLogger(__name__)

VLAN_TYPES = ['vlan', 'trunk', 'none']
# Note: 'pcipt' not supported as of now
ADAPTERS = ['vmxnet3']


class ValidateInputs:

    def __init__(self, inputs):
        self.inputs = inputs

    def raise_validation_error(self, code):
        err = status_messages.get_status(code)
        raise exception.OVSvAppValidationError(err)
        LOG.error(err)

    def validate_CIDR(self, cidr):
        try:
            IPNetwork(cidr)
            return True
        except AddrFormatError:
            raise exception.InvalidCIDRException(
                _("Invalid CIDR has been provided"))

    def _validate_nic_teaming_inputs(self, nic_teaming, net_name):
        if int(nic_teaming['load_balancing']) not in range(1, 6):
            raise exception.OVSvAppValidationError(
                _("'load_balancing' value should be between 1 and 5 for '{}'").
                format(net_name))
        if int(nic_teaming['network_failover_detection']) not in range(
                1, 3):
            raise exception.OVSvAppValidationError(
                _("'network_failover_detection' value"
                  " should be between 1 and 2 "
                  "for '{}'").format(net_name))
        if (nic_teaming['load_balancing'] == '2' and
                nic_teaming['network_failover_detection'] == '2'):
            raise exception.OVSvAppValidationError(
                _("The provided combination of 'load_balancing' & "
                "'network_failover_detection' is not supported for '{}' !").
                format(net_name))

    def _validate_vlan_inputs(self, vlan_range, network_name):
        msg = _("Invalid vlan '{}' has been provided for '{}'").format(
            vlan_range, network_name)
        vlans = []
        vlan_range = util.str2list(vlan_range)
        for item in vlan_range:
            if '-' in item:
                vlans += item.split('-')
                continue
            vlans.append(item)
        for vlan in vlans:
            if not vlan.isdigit():
                raise exception.OVSvAppValidationError(msg)
            if not (int(vlan) >= 0 and int(vlan) <= 4094):
                raise exception.OVSvAppValidationError(msg)

    def _validate_vlan_type(self, vlan, vlan_type, network_name):
        vlan_type = vlan_type.lower()
        msg = ("Invalid 'vlan_type' '{}' has been provided for '{}'"
               .format(vlan_type, network_name))
        if vlan_type not in VLAN_TYPES:
            raise exception.OVSvAppValidationError(msg)
        if vlan_type == 'vlan':
            if not vlan.isdigit():
                raise exception.OVSvAppValidationError(msg)
        if vlan_type == 'trunk' and not vlan:
            raise exception.OVSvAppValidationError(msg)

    def _compare_lists(self, list1, list2):
        return any(True for item in list1 if item in list2)

    def validate_network_inputs(self, dvs_names):
        used_pg_names = list()
        used_tags = list()
        used_dvs = list()
        portgroups = self.inputs.get('portGroups')
        for portgroup in portgroups:
            pg_name = portgroup.get('name')
            if pg_name in used_pg_names:
                raise exception.OVSvAppValidationError(
                    _("Duplicate 'port_group_name' has "
                      "been provided for '{}'").
                    format(pg_name))
            used_pg_names.append(pg_name)
            self._validate_vlan_inputs(portgroup['vlan'], pg_name)
            self._validate_vlan_type(
                portgroup['vlan'], portgroup['vlan_type'], pg_name)
            nic_teaming = portgroup.get('nic_teaming')
            if nic_teaming:
                self._validate_nic_teaming_inputs(nic_teaming, pg_name)
            if portgroup.get('switchName') not in dvs_names:
                raise exception.OVSvAppValidationError(
                    _("Either provide valid 'switchName' for portgroup '{}' "
                    "from 'switches' or remove this portgroup entry.")
                    .format(pg_name))
            used_dvs.append(portgroup.get('switchName'))
            if 'cloud_network_type' in portgroup:
                used_tags.append(util.str2list(portgroup.get(
                    'cloud_network_type').lower()))
        used_tags = list(itertools.chain.from_iterable(used_tags))
        for role in [constants.OVSVAPP_KEY, constants.PROXY_KEY]:
            vm_config = util.get_vmconfig_input(self.inputs, role)
            if not vm_config:
                raise exception.OVSvAppValidationError(
                    _("Invalid 'vm_config' has been provided for '{}'. "
                    "Please check the trunk portGroup name.").format(role))
            conf_pg = util.get_conf_pg(self.inputs, vm_config)
            if not conf_pg:
                raise exception.OVSvAppValidationError(
                    _("Invalid 'portGroup' name has been provided in "
                    "'esx_conf_net' section."))
        if len(used_tags) < 1:
            raise exception.OVSvAppValidationError(
                _("At least one 'cloud_network_type' entry is mandatory in "
                "the 'portGroups' with values as 'vlan' for VLAN deployment, "
                "'vxlan' for VXLAN deployment or 'vlan, vxlan' for both "
                "VLAN+VXLAN deployment."))
        if used_tags.count(vapp_constants.TYPE_VXLAN) > 1:
            raise exception.OVSvAppValidationError(
                _("Multiple 'vxlan' values has been provided for "
                "'cloud_network_type'"))
        return used_dvs

    def validate_dvs_inputs(self):
        dv_switches = self.inputs.get('switches')
        if len(dv_switches) < 2:
            raise exception.OVSvAppValidationError(
                _("At least two entries in 'switches' is mandatory !"))
        empty_pnic_count = 0
        used_dvs_names = list()
        for dvs in dv_switches:
            dvs_name = dvs['name']
            if dvs_name in used_dvs_names:
                raise exception.OVSvAppValidationError(
                    _("Duplicate 'name' has been provided for '{}'")
                    .format(dvs_name))
            used_dvs_names.append(dvs_name)
            mtu = dvs['mtu']
            if mtu:
                msg = _("Invalid MTU has been "
                        "provided for '{}'").format(dvs_name)
                if not isinstance(mtu, int):
                    if not mtu.isdigit():
                        raise exception.OVSvAppValidationError(msg)
                    mtu = int(mtu)
                if mtu not in xrange(1500, 9999):
                    raise exception.OVSvAppValidationError(msg)
            if not dvs.get('physical_nics'):
                empty_pnic_count += 1
        if empty_pnic_count != 1:
            raise exception.OVSvAppValidationError(
                _("Only one entry in 'switches' should have empty "
                "'physical_nics' for OVSvApp Trunk DVS creation."))
        return used_dvs_names

    def validate_ip_inputs(self):
        ip_config = self.inputs.get('esx_conf_net')
        self.validate_CIDR(ip_config['cidr'])
        ip_range = [ip_config['start_ip'], ip_config['end_ip']]
        if all(ip_range):
            if (not IPAddress(ip_config['start_ip']) in
                    IPNetwork(ip_config['cidr'])):
                raise exception.OVSvAppValidationError(
                    _("'start_ip' is not within 'cidr'"))
            if (not IPAddress(ip_config['end_ip']) in
                    IPNetwork(ip_config['cidr'])):
                raise exception.OVSvAppValidationError(
                    _("'end_ip' is not within 'cidr'"))
            if ip_config['start_ip'] == ip_config['gateway']:
                raise exception.OVSvAppValidationError(
                    _("'start_ip' and 'gateway' can not be same."))
        else:
            if ip_range.count('') == 1:
                raise exception.OVSvAppValidationError(
                    _("Either 'start_ip' or 'end_ip' has not been provided ! "
                    "Either provide both or don't provide both of them."))

    def _validate_vnics(self, vm_config, pg_names, role):
        used_pci_ids = list()
        used_pg_names = list()
        used_eths = list()
        if not vm_config:
            raise exception.OVSvAppValidationError(
                _("Invalid configuration has "
                  "been provided for {}").format(role))
        nics = vm_config.get('nics')
        server_role = vm_config.get('server_role')
        eths = ['eth'.join(['', str(i)]) for i in xrange(len(nics))]
        for nic in nics:
            device = nic.get('device')
            if device not in eths:
                raise exception.OVSvAppValidationError(
                    _("Invalid device '{}' has been provided for '{}'")
                    .format(device, server_role))
            if device in used_eths:
                raise exception.OVSvAppValidationError(
                    _("Duplicate device '{}' has been provided for '{}'")
                    .format(device, server_role))
            used_eths.append(device)
            nic_type = nic.get('type').lower()
            if nic_type not in ADAPTERS:
                raise exception.OVSvAppValidationError(
                    _("Invalid network adapter 'type' has been provided "
                    "for '{}'").format(server_role))
            if nic_type == 'pcipt':
                if not nic.get('pci_id'):
                    raise exception.OVSvAppValidationError(
                        _("Device 'type' is pcipt but 'pci_id' has not "
                        "been provide for '{}'").format(server_role))
                else:
                    used_pci_ids.append(nic.get('pci_id'))
            else:
                pg_name = nic.get('portGroup')
                if pg_name not in pg_names:
                    raise exception.OVSvAppValidationError(
                        _("Invalid 'portGroup' name has been provided for "
                        "'{}'").format(server_role))
                if pg_name in used_pg_names:
                    raise exception.OVSvAppValidationError(
                        _("Duplicate 'portGroup' name has been provided in "
                        "the 'nics' for '{}'").format(server_role))
                used_pg_names.append(pg_name)
        return used_pci_ids

    def validate_vmconfig_inputs(self):
        roles = [constants.OVSVAPP_KEY, constants.PROXY_KEY]
        used_pci_ids = list()
        port_groups = self.inputs.get('portGroups')
        pg_names = [pg.get('name') for pg in port_groups]
        lifecycle_manager = self.inputs.get('lifecycle_manager')
        if not lifecycle_manager.get('ssh_key'):
            raise exception.OVSvAppValidationError(
                _("Invalid 'ssh_key' has been provided"))
        for role in roles:
            vm_config = util.get_vmconfig_input(self.inputs, role)
            used_pci_ids += self._validate_vnics(vm_config, pg_names, role)
        if len(used_pci_ids) != len(set(used_pci_ids)):
            raise exception.OVSvAppValidationError(
                _("Found same 'pci_id' in the 'nics' for both OVSvApp & "
                "ESX Compute Proxy"))

    def validate_inputs(self, setup_network=False):
        if setup_network:
            dvs_names = self.validate_dvs_inputs()
            used_dvs = self.validate_network_inputs(dvs_names)
            unused_dvs = list(set(dvs_names) - set(used_dvs))
            if len(unused_dvs) > 0:
                raise exception.OVSvAppValidationError(
                    _("Remove unused switch entry '{}' "
                    "from 'switches'").format(unused_dvs))
        else:
            self.validate_ip_inputs()
            self.validate_vmconfig_inputs()
