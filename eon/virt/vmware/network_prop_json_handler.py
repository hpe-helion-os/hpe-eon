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

from eon.hlm_facade import hlm_facade_handler
from eon.virt.vmware import constants
from eon.openstack.common import log as logging
from eon.virt.common import utils

LOG = logging.getLogger(__name__)


class NetworkProperties(object):

    def __init__(self, hlm_version=None, switches=None, portgroups=None,
                 esx_conf_net=None, lifecycle_manager=None, vm_config=None):
        self.hlm_version = hlm_version
        self.switches = switches
        self.portGroups = portgroups
        self.esx_conf_net = esx_conf_net
        self.lifecycle_manager = lifecycle_manager
        self.vm_config = vm_config

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=True, indent=1)


class Switch(object):

    def __init__(self, _type=None, name=None, physical_nics=None, mtu=None):
        self.type = _type
        self.name = name
        self.physical_nics = physical_nics
        self.mtu = mtu


class Portgroup(object):

    def __init__(self, name=None, nic_teaming=None, vlan_type=None,
                 vlan=None, switch_name=None):
        self.name = name
        self.nic_teaming = nic_teaming
        self.vlan_type = vlan_type
        self.vlan = vlan
        self.switchName = switch_name


class VmConfig(object):
    def __init__(self, server_role=None, template_name=None,
                 cpu=None, memory_in_mb=None, nics=None):
        self.server_role = server_role
        self.template_name = template_name
        self.cpu = cpu
        self.memory_in_mb = memory_in_mb
        self.nics = nics


class VmNic(object):
    def __init__(self, device=None, type_=None, pci_id=None, port_group=None):
        self.device = device
        self.type = type_
        self.pci_id = pci_id
        self.portGroup = port_group


class NICTeaming(object):
    def __init__(self, network_failover_detection=None,
                 notify_switches=None, load_balancing=None, active_nics=None):
        self.network_failover_detection = network_failover_detection
        self.notify_switches = notify_switches
        self.load_balancing = load_balancing
        self.active_nics = active_nics


class ESXConfNet(object):
    def __init__(self, start_ip=None, cidr=None, end_ip=None,
                 gateway=None, portGroup=None):
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.cidr = cidr
        self.gateway = gateway
        self.portGroup = portGroup


class LifeCycleManager(object):
    def __init__(self, ip_address=None, ssh_key=None, user=None):
        self.ip_address = ip_address
        self.ssh_key = ssh_key
        self.user = user


def _get_network_by_group(networks, network_group_name):
    for network in networks:
        if network.get('network-group') == network_group_name:
            return network


def _get_networks(hlm_facade):
    network_info = {}
    networks = hlm_facade.get_networks()
    for network in networks:
        network_info[network.get("name")] = network
    return network_info


def _get_network_groups_info(hlm_facade):
    network_groups = hlm_facade.get_network_groups()
    return network_groups


def _get_deployer_info(hlm_facade):
    deployer_info = hlm_facade.get_server_by_id("deployer")
    return deployer_info


def _get_conf_allocation_info(context):
    network_info = utils.get_global_pass_thru_data(
            context, constants.HPECS)
    conf_network_info = network_info.get("networks")[0]
    return conf_network_info


def _get_switch_to_network(input_data):
    switch_to_network = {}
    cloud_trunks = input_data.get("cloud_trunks")
    for cloud_trunk in cloud_trunks:
        switch_name = cloud_trunk['name']
        switch_to_network[switch_name] = cloud_trunk['network_name']
    return switch_to_network


def _get_ovsvapp_network_mapping(hlm_facade, network_info,
                                 network_to_portgroup):
    interface_to_portgroup = {}
    ovsvapp_interface = hlm_facade.get_interfaces_by_name(
                                        constants.OVSVAPP_INTERFACES)
    network_interfaces = ovsvapp_interface.get("network-interfaces")
    for interface in network_interfaces:
        network_groups = interface.get('network-groups')
        if network_groups:
            network_group_name = network_groups[0]
            network = _get_network_by_group(network_info.values(),
                                            network_group_name)
            if network:
                interface_to_portgroup[interface.get('name')] = (
                                network_to_portgroup.get(network.get("name")))
    return interface_to_portgroup


def _get_network_to_portgroup_mapping(input_data):
    network_to_portgroup = {}
    cloud_trunks = input_data.get("cloud_trunks")
    for cloud_trunk in cloud_trunks:
        portgroup_name = cloud_trunk['name'] + "-pg"
        network_to_portgroup[cloud_trunk.get('network_name')] = portgroup_name
    return network_to_portgroup


def _get_conf_network(network_info, network_groups):
    for network_group in network_groups:
        endpoints = network_group.get("component-endpoints")
        if endpoints and "lifecycle-manager" in endpoints:
            for network in network_info.values():
                net_group = network.get("network-group")
                if net_group == network_group.get("name"):
                    return network


def _get_network(network_info, network_groups, role_name):
    # TODO: Need better way to get DCM/CLM network details
    for network_group in network_groups:
        load_balancers = network_group.get("load-balancers")
        if load_balancers:
            for load_balancer in load_balancers:
                if load_balancer.get("roles"):
                    roles = load_balancer.get("roles")
                    if roles and role_name in roles:
                        for network in network_info.values():
                            net_group = network.get("network-group")
                            if net_group == network_group.get("name"):
                                return network


def _get_network_group(network_groups, cloud_nw_group_name):
    for network_group in network_groups:
        if network_group['name'] == cloud_nw_group_name:
            return network_group


def _get_cloud_network_group_info(cloud_data_network, network_groups):
    cloud_network_type = None
    cloud_nw_group_name = cloud_data_network.get("network-group")
    cloud_network_group = _get_network_group(network_groups,
                                             cloud_nw_group_name)
    tags = cloud_network_group.get("tags")
    if tags:
        for tag in tags:
            if isinstance(tag, dict) and (
                    constants.NETWORK_TYPE_VLAN in tag.keys()):
                cloud_network_type = constants.VLAN
            elif isinstance(tag, dict) and (
                    constants.NETWORK_TYPE_VXLAN in tag.keys()):
                cloud_network_type = constants.VXLAN
    return cloud_network_type


def _build_management_switch(mgmt_data):
    mgmt_switch = Switch()
    mgmt_switch.type = constants.DVSWITCH
    mgmt_switch.name = mgmt_data.get("name")
    mgmt_switch.physical_nics = mgmt_data.get("nics")
    mgmt_switch.mtu = mgmt_data.get("mtu")
    return mgmt_switch


def _build_cloudtrunk_switches(cloudtrunk_data):
    cloud_trunk_switches = []
    for data in cloudtrunk_data:
        cloud_trunk_switch = Switch()
        cloud_trunk_switch.type = constants.DVSWITCH
        cloud_trunk_switch.name = data.get("name")
        cloud_trunk_switch.physical_nics = data.get("nics")
        cloud_trunk_switch.mtu = data.get("mtu")
        cloud_trunk_switches.append(cloud_trunk_switch)
    return cloud_trunk_switches


def _build_trunk_switch():
    trunk_switch = Switch(constants.DVSWITCH, constants.TRUNK_DVS,
                          "", constants.DEFAULT_MTU)
    return trunk_switch


def _build_portgroup(mgmt_switch, network, network_type):
    portgroup = Portgroup()
    nics = mgmt_switch.physical_nics.split(",")
    nic_teaming = NICTeaming("1", "yes", "1",
                             nics[0])
    portgroup.nic_teaming = nic_teaming
    portgroup.switchName = mgmt_switch.name
    # get from hlm_facade
    tagged_vlan = network.get("tagged-vlan")
    portgroup.vlan_type = "trunk" if tagged_vlan else "none"
    portgroup.vlan = str(network.get("vlanid")) if tagged_vlan else ""
    if network_type == constants.CONF_NETWORK_TYPE:
        portgroup.name = "conf-" + mgmt_switch.name + "-pg"
    elif network_type == constants.CLM_NETWORK_TYPE:
        portgroup.name = mgmt_switch.name + "-pg"
    return portgroup


def _build_cloudtrunk_portgroups(cloud_trunk_switches, network_info,
                                 network_groups,
                                 switch_to_network):
    cloud_trunk_portgroups = []
    for cloud_trunk_switch in cloud_trunk_switches:
        portgroup = Portgroup()
        nics = cloud_trunk_switch.physical_nics.split(",")
        nic_teaming = NICTeaming("1", "yes", "1",
                                 nics[0])
        portgroup.nic_teaming = nic_teaming
        portgroup.switchName = cloud_trunk_switch.name
        # get from hlm_facade
        cloud_trunk_network = network_info.get(switch_to_network.get(
                                            cloud_trunk_switch.name))
        if not cloud_trunk_network:
            msg = (_("Network name specified for cloud data switch "
                    "%s is not correct. Provide valid cloud data trunk"
                    " network name") % cloud_trunk_switch.name)
            raise Exception(msg)
        cloud_network_type = (
                    _get_cloud_network_group_info(cloud_trunk_network,
                                                  network_groups))
        if cloud_network_type == constants.VLAN:
            portgroup.vlan_type = "trunk"
            portgroup.vlan = "1-4094"
            portgroup.cloud_network_type = cloud_network_type
        elif cloud_network_type == constants.VXLAN:
            tagged_vlan = cloud_trunk_network.get("tagged-vlan")
            portgroup.vlan_type = "trunk" if tagged_vlan else "none"
            portgroup.vlan = (str(cloud_trunk_network.get("vlanid"))
                              if tagged_vlan else "")
            portgroup.cloud_network_type = cloud_network_type
        portgroup.name = cloud_trunk_switch.name + "-pg"
        cloud_trunk_portgroups.append(portgroup)
    return cloud_trunk_portgroups


def _build_trunk_portgroup(trunk_switch):
    trunk_portgroup = Portgroup(name="trunk-pg", nic_teaming=None,
                                 vlan_type="trunk", vlan="1-4094",
                                 switch_name=trunk_switch.name)
    del trunk_portgroup.nic_teaming
    return trunk_portgroup


def _build_esx_conf_network(conf_network_info, conf_network,
                            conf_portgroup_name):
    start_ip = None
    end_ip = None
    network_members = conf_network_info.get("members")[0]
    conf_cidr = network_members.get("cidr")
    esx_allocation = network_members.get("allocations").get("esx")
    if esx_allocation:
        start_ip = esx_allocation[0]
        end_ip = esx_allocation[1]
    esx_conf_net = ESXConfNet()
    esx_conf_net.cidr = conf_cidr
    esx_conf_net.start_ip = start_ip
    esx_conf_net.end_ip = end_ip
    esx_conf_net.gateway = conf_network.get("gateway-ip")
    esx_conf_net.portGroup = conf_portgroup_name
    return esx_conf_net


def _build_compute_vm_config(conf_pg_name, mgmt_pg_name):
    vmconfig = VmConfig()
    vmnics = []
    vmconfig.server_role = constants.ESX_COMPUTE_ROLE
    vmconfig.cpu = constants.CPU
    vmconfig.memory_in_mb = constants.MEMORY_IN_MB
    vmconfig.template_name = constants.HLINUX_OVA_TEMPLATE_NAME
    conf_nic = VmNic(device="eth0", type_="vmxnet3", pci_id="",
                port_group=conf_pg_name)
    vmnics.append(conf_nic)
    mgmt_nic = VmNic(device="eth1", type_="vmxnet3", pci_id="",
                port_group=mgmt_pg_name)
    vmnics.append(mgmt_nic)
    vmconfig.nics = vmnics
    return vmconfig


def _build_ovsvapp_vm_config(conf_pg_name, mgmt_pg_name,
                             trunk_pg_name,
                             cloud_trunk_pg_names,
                             interface_to_portgroup):
    vmconfig = VmConfig()
    vmnics = []
    vmconfig.server_role = constants.OVSVAPP_ROLE
    vmconfig.cpu = constants.CPU
    vmconfig.memory_in_mb = constants.MEMORY_IN_MB
    vmconfig.template_name = constants.HLINUX_OVA_TEMPLATE_NAME
    conf_nic = VmNic(device="eth0", type_="vmxnet3", pci_id="",
                port_group=conf_pg_name)
    vmnics.append(conf_nic)
    mgmt_nic = VmNic(device="eth1", type_="vmxnet3", pci_id="",
                port_group=mgmt_pg_name)
    vmnics.append(mgmt_nic)
    trunk_nic = VmNic(device="eth2", type_="vmxnet3",
                      pci_id="",
                      port_group=trunk_pg_name)
    vmnics.append(trunk_nic)
    nic_number = 3
    for _ in range(len(cloud_trunk_pg_names)):
        nic_interface = "eth" + str(nic_number)
        cloud_trunk_nic = VmNic(device=nic_interface, type_="vmxnet3",
                                pci_id="",
                                port_group=interface_to_portgroup.get(
                                                        nic_interface))
        vmnics.append(cloud_trunk_nic)
        nic_number += 1
    vmconfig.nics = vmnics
    return vmconfig


def _build_lifecycle_manager_info(deployer_ip):
    ssh_key = None
    with open(constants.SSH_KEY_FILE) as f:
        ssh_key = f.read()
        ssh_key = ssh_key.rstrip()
    ssh_key_list = ssh_key.split(" ")
    user_name = ssh_key_list[2].split("@")[0]
    lifecycle_manager = LifeCycleManager(deployer_ip, ssh_key,
                                         user_name)
    return lifecycle_manager


def populate_network_properties(context, input_data):
    try:
        switches = []
        portgroups = []
        vm_config = []
        hlm_facade = hlm_facade_handler.HLMFacadeWrapper(context)
        # get the required data from hlm facade
        deployer_info = _get_deployer_info(hlm_facade)
        network_info = _get_networks(hlm_facade)
        network_groups = _get_network_groups_info(hlm_facade)
        conf_network_info = _get_conf_allocation_info(context)
        conf_network = _get_conf_network(network_info, network_groups)
        if not conf_network:
            raise Exception(_("CONF network is not defined in the "
                              "input model"))
        dcm_network = _get_network(network_info, network_groups, "admin")
        if not dcm_network:
            raise Exception(_("DCM network is not defined in the input model"))
        clm_network = _get_network(network_info, network_groups, "internal")
        if not clm_network:
            raise Exception(_("CLM network is not defined in the input model"))

        switch_to_network = _get_switch_to_network(input_data)
        network_to_portgroup = _get_network_to_portgroup_mapping(input_data)
        ovsvapp_interface_to_portgroup = (
                                _get_ovsvapp_network_mapping(hlm_facade,
                                                        network_info,
                                                        network_to_portgroup))
        # Build the network properties
        network_prop = NetworkProperties()
        network_prop.hlm_version = constants.HLM_VERSION
        mgmt_switch = _build_management_switch(input_data.get("mgmt_trunk"))
        switches.append(mgmt_switch)
        conf_portgroup = _build_portgroup(mgmt_switch, conf_network,
                                          constants.CONF_NETWORK_TYPE)
        portgroups.append(conf_portgroup)
        mgmt_portgroup = _build_portgroup(mgmt_switch, clm_network,
                                          constants.CLM_NETWORK_TYPE)
        # TODO: Currently assumed that CLM and DCM are part of same portgroup.
        # Need to handle if they need to be in different portgroups
        dcm_vlanid = dcm_network.get("vlanid")
        if dcm_vlanid and mgmt_portgroup.vlan != str(dcm_vlanid):
            mgmt_portgroup.vlan = (mgmt_portgroup.vlan + "," + str(dcm_vlanid))
        portgroups.append(mgmt_portgroup)
        vm_compute_config = _build_compute_vm_config(conf_portgroup.name,
                                                     mgmt_portgroup.name)
        vm_config.append(vm_compute_config)
        cloud_trunk_switches = _build_cloudtrunk_switches(
                                            input_data.get("cloud_trunks"))
        switches.extend(cloud_trunk_switches)
        trunk_switch = _build_trunk_switch()
        switches.append(trunk_switch)
        cloud_trunk_portgroups = _build_cloudtrunk_portgroups(
                                                        cloud_trunk_switches,
                                                        network_info,
                                                        network_groups,
                                                        switch_to_network)
        cloud_trunk_pg_names = [portgroup.name for portgroup in
                                cloud_trunk_portgroups]
        portgroups.extend(cloud_trunk_portgroups)
        trunk_portgroup = _build_trunk_portgroup(trunk_switch)
        portgroups.append(trunk_portgroup)
        vm_ovsvapp_config = _build_ovsvapp_vm_config(conf_portgroup.name,
                                                mgmt_portgroup.name,
                                                trunk_portgroup.name,
                                                cloud_trunk_pg_names,
                                                ovsvapp_interface_to_portgroup)
        vm_config.append(vm_ovsvapp_config)
        lifecycle_manager = _build_lifecycle_manager_info(
                                                deployer_info.get("ip-addr"))
        esx_conf_net = _build_esx_conf_network(conf_network_info, conf_network,
                                               conf_portgroup.name)
        network_prop.switches = switches
        network_prop.portGroups = portgroups
        network_prop.vm_config = vm_config
        network_prop.esx_conf_net = esx_conf_net
        network_prop.lifecycle_manager = lifecycle_manager
        return network_prop.to_JSON()
    except Exception as e:
        LOG.exception(e)
        raise
