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

from eon.common.exception import OVSvAppException
from eon.openstack.common import lockutils
import eon.common.log as logging
from eon.deployer import util
from eon.deployer.network.ovsvapp.util import vapp_constants as const

LOG = logging.getLogger(__name__)


class DVSAdapter:

    def __init__(self):
        self.nic_teaming = (
            vim.dvs.VmwareDistributedVirtualSwitch.UplinkPortTeamingPolicy())
        self.dv_pg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
        self.dv_pg_spec.defaultPortConfig = (
            vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy())
        self.dv_pg_spec.defaultPortConfig.vlan = None
        self.dv_pg_spec.defaultPortConfig.securityPolicy = (
            vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy())
        self.load_balance = {'1': 'loadbalance_srcid',
                             '2': 'loadbalance_ip',
                             '3': 'loadbalance_srcmac',
                             '4': 'loadbalance_loadbased',
                             '5': 'failover_explicit'}
        self.failover = {'1': False, '2': True}

    def _get_used_pnics(self, host):
        used_pnics = []
        for vswitch in host['config.network.vswitch']:
            used_pnics += vswitch.pnic
        for proxy_switch in host['config.network.proxySwitch']:
            used_pnics += proxy_switch.pnic
        return used_pnics

    def _get_free_physical_nic(self, host, host_pnic):
        pnic_device = self._validate_host_pnic(host, host_pnic)
        used_pnics = self._get_used_pnics(host)
        if pnic_device:
            if isinstance(pnic_device, list):
                for pnic in used_pnics:
                    phys_nic = pnic[pnic.rfind('-') + 1:]
                    if phys_nic in pnic_device:
                        LOG.error("Busy/used physical nic '%s'" % phys_nic)
                        return
                return pnic_device
            elif isinstance(pnic_device, str):
                for pnic in used_pnics:
                    phys_nic = pnic[pnic.rfind('-') + 1:]
                    if phys_nic == pnic_device:
                        LOG.error("Provided physical nic '%s' is "
                                  "used/busy" % pnic_device)
                        return
                return pnic_device

    def _validate_host_pnic(self, host, physnic):
        all_host_pnics = [pnic.device for pnic in host['config.network.pnic']]
        if isinstance(physnic, list):
            uplink_nics = [nic for nic in physnic if nic in all_host_pnics]
            return uplink_nics
        elif isinstance(physnic, str):
            if physnic not in all_host_pnics:
                return
            else:
                return physnic

    def _set_security_policy(self, promiscous=False,
                             forged_transmit=False):
        """
        Creates requested security policy for the DVS
        """
        self.dv_pg_spec.defaultPortConfig.securityPolicy.allowPromiscuous = (
            vim.BoolPolicy(value=promiscous))
        self.dv_pg_spec.defaultPortConfig.securityPolicy.forgedTransmits = (
            vim.BoolPolicy(value=forged_transmit))

    def _get_vlan_range(self, raw_vlan_range):
        vlan_range = []
        for item in raw_vlan_range:
            if '-' in item:
                lan_range = map(int, item.split('-'))
                vlan_range.append(vim.NumericRange(start=lan_range[0],
                                                   end=lan_range[1]))
            else:
                item = int(item)
                vlan_range.append(vim.NumericRange(start=item, end=item))
        return vlan_range

    def _set_trunk_vlan_spec(self, vlan_range):
        """
        Creates trunk vlan spec for the DVS
        """
        self.dv_pg_spec.defaultPortConfig.vlan = (
            vim.dvs.VmwareDistributedVirtualSwitch.TrunkVlanSpec())
        self.dv_pg_spec.defaultPortConfig.vlan.vlanId = self._get_vlan_range(
            vlan_range)

    def _set_vlan_id_spec(self, vlan):
        self.dv_pg_spec.defaultPortConfig.vlan = (
            vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec())
        self.dv_pg_spec.defaultPortConfig.vlan.vlanId = vlan

    def _set_vlan_spec(self, vlan, vlan_type):
        vlan = util.str2list(vlan)
        if vlan:
            if vlan_type == 'trunk':
                self._set_trunk_vlan_spec(vlan)
            elif vlan_type == 'vlan':
                self._set_vlan_id_spec(int(vlan[0]))
            elif vlan_type == 'none':
                self._set_vlan_id_spec(0)
        else:
            self._set_vlan_id_spec(0)

    def _fetch_uplink_dv_ports(self, dvs):
        dv_ports = dvs.FetchDVPorts(vim.dvs.PortCriteria(uplinkPort=True))
        return dv_ports

    def _get_uplink_nic_map(self, dvs):
        uplink_nic_map = dict()
        dv_ports = self._fetch_uplink_dv_ports(dvs)
        for dv_port in dv_ports:
            uplink_name = dv_port.config.name
            if hasattr(dv_port.connectee, 'nicKey'):
                pnic = dv_port.connectee.nicKey
                uplink_nic_map[pnic] = uplink_name
        return uplink_nic_map

    def _get_num_dvs_nics(self, data_dvs):
        pnics = []
        dv_ports = self._fetch_uplink_dv_ports(data_dvs)
        for dv_port in dv_ports:
            if hasattr(dv_port.connectee, 'nicKey'):
                pnics.append(dv_port.connectee.nicKey)
        return len(list(set(pnics)))

    def _set_uplink_port_order(self, dvs, active_nics):
        active_nics = util.str2list(active_nics)
        nic_map = self._get_uplink_nic_map(dvs)
        active_uplinks = []
        standby_uplinks = []
        if active_nics:
            active_uplinks = [nic_map.get(nic) for nic in active_nics]
            for __, v in nic_map.iteritems():
                if v not in active_uplinks:
                    standby_uplinks.append(v)
        else:
            active_uplinks.append('dvUplink0')
            for __, value in nic_map.iteritems():
                if value == 'dvUplink0':
                    continue
                standby_uplinks.append(value)

    def _set_notify_switches_config(self, value):
        self.nic_teaming.notifySwitches = vim.BoolPolicy(
            value=util.str2bool(value))

    def _set_failover_detection_config(self, key):
        self.nic_teaming.failureCriteria = (
            vim.dvs.VmwareDistributedVirtualSwitch.FailureCriteria(
                checkBeacon=vim.BoolPolicy(
                    value=self.failover.get(key))))

    def _set_loadbalancing_config(self, key):
        self.nic_teaming.policy = vim.StringPolicy(
            value=self.load_balance.get(key))

    def _set_nic_teaming_policy(self, dvs, network):
        teaming_input = network.get("nic_teaming")
        self._set_notify_switches_config(teaming_input['notify_switches'])
        self._set_failover_detection_config(
            teaming_input['network_failover_detection'])
        self._set_loadbalancing_config(teaming_input['load_balancing'])
        self._set_uplink_port_order(dvs, teaming_input['active_nics'])
        self.dv_pg_spec.defaultPortConfig.uplinkTeamingPolicy = (
            self.nic_teaming)

    def add_dv_port_groups(self, si, dv_switch, pg):
        """
        Create and attach auto expandable DV Port Group to the DVS
        @return: DV Port Group
        """
        self.dv_pg_spec.name = pg['name']
        self.dv_pg_spec.description = const.OVS_VAPP_IDENTIFIER
        self.dv_pg_spec.type = (
            vim.dvs.DistributedVirtualPortgroup.PortgroupType.earlyBinding)
        self.dv_pg_spec.autoExpand = True
        LOG.debug("Adding port group %s to DVS %s ..."
                  % (pg['name'], dv_switch.name))
        task = dv_switch.AddDVPortgroup_Task([self.dv_pg_spec])
        ret_type = util.VMwareUtils.wait_for_task(task, si)
        if isinstance(ret_type, vim.fault.VimFault):
            raise OVSvAppException(_("Error occurred while "
                                   "creating DVPortgroup: %s") % ret_type)
        LOG.info("Successfully added port group %s to DVS %s"
                 % (pg['name'], dv_switch.name))

    def _create_host_config_spec(self, hosts, pnic_device):
        pnic_device = util.str2list(pnic_device)
        dvs_host_configs = []
        for host in hosts:
            pnic_spec = []
            dvs_host_config = vim.dvs.HostMember.ConfigSpec()
            dvs_host_config.operation = vim.ConfigSpecOperation.add
            if pnic_device:
                dvs_host_config.backing = vim.dvs.HostMember.PnicBacking()
                phys_nic = self._get_free_physical_nic(host, pnic_device)
                if not phys_nic:
                    msg = _("Provided physical nic/nics are either used/busy "
                           "or they don't exist. Couldn't attach the host in "
                           "DVS.")
                    raise OVSvAppException(msg)
                for pnic in phys_nic:
                    pnic_spec.append(vim.dvs.HostMember.
                                     PnicSpec(pnicDevice=pnic.lower()))
                dvs_host_config.backing.pnicSpec = pnic_spec
            dvs_host_config.host = host['obj']
            dvs_host_configs.append(dvs_host_config)
        return dvs_host_configs

    def _get_dvs_create_spec(self, dvs_name, pnic_device, mtu):
        dvs_create_spec = vim.DistributedVirtualSwitch.CreateSpec()
        dvs_config_spec = vim.dvs.VmwareDistributedVirtualSwitch.ConfigSpec()
        dvs_config_spec.name = dvs_name
        dvs_config_spec.description = const.OVS_VAPP_IDENTIFIER
        dvs_config_spec.maxPorts = const.VC_MAX_PORTS
        dvs_config_spec.maxMtu = mtu
        dvs_config_spec.uplinkPortPolicy = \
            vim.DistributedVirtualSwitch.NameArrayUplinkPortPolicy()
        if pnic_device:
            uplinks = ['dvUplink'.join(['', str(i)]) for i in
                       xrange(len(pnic_device))]
            dvs_config_spec.uplinkPortPolicy.uplinkPortName = uplinks
        else:
            dvs_config_spec.uplinkPortPolicy.uplinkPortName = ['dvUplink']
        min_version = ''.join([const.MIN_SUPPORTED_VERSION, '.0'])
        dvs_create_spec.productInfo = vim.dvs. \
            ProductSpec(version=min_version)
        return dvs_create_spec, dvs_config_spec

    def create_dvSwitch(
            self, si, network_folder, hosts, dvs_name, pnic_device, mtu):
        """
        Create a Distributed Virtual Switch
        @return: Distributed Virtual Switch
        """
        dvs_create_spec, dvs_config_spec = \
            self._get_dvs_create_spec(dvs_name, pnic_device, mtu)
        dvs_host_configs = self._create_host_config_spec(
            hosts, pnic_device)
        dvs_config_spec.host = dvs_host_configs
        dvs_create_spec.configSpec = dvs_config_spec
        task = network_folder.CreateDVS_Task(dvs_create_spec)
        dv_switch = util.VMwareUtils.wait_for_task(task, si)
        if not isinstance(dv_switch, vim.DistributedVirtualSwitch):
            raise OVSvAppException(_("Error occurred while creating DVS: %s") %
                                   dvs_name)
        LOG.info("Successfully created DVS '%s'" % dvs_name)
        return dv_switch

    def create_dvs_skeleton(
            self, si, network_folder, dvs_name, pnic_device, mtu):
        dvs_create_spec, dvs_config_spec = \
            self._get_dvs_create_spec(dvs_name, pnic_device, mtu)
        dvs_create_spec.configSpec = dvs_config_spec
        task = network_folder.CreateDVS_Task(dvs_create_spec)
        dv_switch = util.VMwareUtils.wait_for_task(task, si)
        if not isinstance(dv_switch, vim.DistributedVirtualSwitch):
            raise OVSvAppException(_("Error occurred while creating DVS: %s") %
                                   dvs_name)
        LOG.info("Successfully created DVS '%s'" % dvs_name)
        return dv_switch

    @lockutils.synchronized("set-network-lock")
    def reconfigure_dvs(self, si, dvs, hosts, pnic_device=None):
        hosts_in_dvs = [member.config.host for member in dvs.config.host]
        hosts = [host for host in hosts if host['obj'] not in hosts_in_dvs]
        if hosts:
            dvs_config_spec = vim.DistributedVirtualSwitch.ConfigSpec()
            dvs_config_spec.configVersion = dvs.config.configVersion
            dvs_host_configs = \
                self._create_host_config_spec(hosts, pnic_device)
            dvs_config_spec.host = dvs_host_configs
            task = dvs.ReconfigureDvs_Task(dvs_config_spec)
            output = util.VMwareUtils.wait_for_task(task, si)
            if isinstance(output, vim.fault.VimFault):
                LOG.exception(output)
                raise Exception(_("Error occurred while configuring {}")
                                .format(dvs.name))
            LOG.info("Successfully reconfigured DVS {}".format(dvs.name))

    @lockutils.synchronized("set-network-lock")
    def reconfigure_dv_portgroup(self, si, pg, dv_switch, network):
        pnics = self._get_num_dvs_nics(dv_switch)
        self.dv_pg_spec.name = pg.name
        self.dv_pg_spec.description = pg.config.description
        self.dv_pg_spec.configVersion = pg.config.configVersion
        if pnics > 0:
            self._set_vlan_spec(network['vlan'], network['vlan_type'].lower())
            self._set_nic_teaming_policy(dv_switch, network)
            if ('cloud_network_type' in network and
                    const.TYPE_VLAN in network['cloud_network_type'].lower()):
                self._set_security_policy(True, True)
            else:
                self._set_security_policy()
        else:
            self._set_vlan_spec('1-4094', 'trunk')
            self._set_security_policy(True, True)
            self.dv_pg_spec.defaultPortConfig.uplinkTeamingPolicy = (
                pg.config.defaultPortConfig.uplinkTeamingPolicy)
        task = pg.ReconfigureDVPortgroup_Task(spec=self.dv_pg_spec)
        output = util.VMwareUtils.wait_for_task(task, si)
        if isinstance(output, vim.fault.VimFault):
            LOG.exception(output)
            raise OVSvAppException(_("Error occurred while configuring {}")
                                   .format(pg.name))
        LOG.info("Successfully reconfigured port group {}".format(pg.name))
