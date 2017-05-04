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

import time

from pyVmomi import vim
from pyVmomi import vmodl

from eon.common.exception import OVSvAppException
import eon.common.log as logging
from eon.deployer import constants
from eon.deployer import util
from eon.deployer.network.ovsvapp.util import vapp_constants as const
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil

LOG = logging.getLogger(__name__)


class Cleanup:

    def __init__(self, input_json):
        self.inputs = input_json
        vc = input_json['vcenter_configuration']
        service_instance = util.VMwareUtils.get_vcenter_session(
            vc['ip_address'], vc['port'], vc['username'], vc['password'])
        self.si = service_instance
        self.content = service_instance.RetrieveContent()
        dc = util.VMwareUtils.get_data_center(self.content, vc['datacenter'])
        self.dc_name = dc['name']
        self.network_folder = dc['networkFolder']
        self.vm_folder = dc['vmFolder']
        self.cluster = util.VMwareUtils.get_cluster(
            self.content, dc['hostFolder'], vc['cluster_moid'])

    def _destroy_network_task(self, network):
        network_name = network.name
        try:
            members = None
            if isinstance(network, vim.DistributedVirtualSwitch):
                members = network.summary.vm
            elif isinstance(network, vim.dvs.DistributedVirtualPortgroup):
                members = network.vm
            if not members:
                delete_task = network.Destroy_Task()
                util.VMwareUtils.wait_for_task(delete_task, self.si)
                LOG.info("Successfully deleted '{}".format(network_name))
        except vmodl.MethodFault as e:
            msg = (_("Exception occurred while deleting '{}' : {}")
                   .format(network_name, e.faultMessage[0].message))
            LOG.exception(msg)
            raise OVSvAppException(msg)
        except Exception as e:
            LOG.exception(e)
            raise OVSvAppException(reason=e)

    def teardown_network(self):
        for pg in self.network_folder.childEntity:
            if isinstance(pg, vim.DistributedVirtualPortgroup):
                try:
                    dvs = pg.config.distributedVirtualSwitch
                    # If OVSvApp installer has created the switch then destroy
                    # it along with the pgs.
                    if dvs.config.description == const.OVS_VAPP_IDENTIFIER:
                        self._destroy_network_task(dvs)
                        continue
                    # Switch has been created by user and not by OVSvApp !
                    # If PG has been created by OVSvApp then destroy it.
                    if pg.config.description == const.OVS_VAPP_IDENTIFIER:
                        self._destroy_network_task(pg)
                except vmodl.fault.ManagedObjectNotFound:
                    pass

    def _poweroff_ovsvapp_task(self, ovsvapp):
        if ovsvapp['runtime.powerState'] == 'poweredOn':
            poweroff_task = ovsvapp['obj'].PowerOff()
            util.VMwareUtils.wait_for_task(poweroff_task, self.si)
            LOG.info("Successfully Powered off '{}'".format(ovsvapp['name']))

    def _shutdown_ovsvapp_task(self, ovsvapp):
        ovsvapp_name = ovsvapp['name']
        try:
            LOG.info("Initiating a soft shutdown on '{}' ..."
                     .format(ovsvapp_name))
            ovsvapp['obj'].ShutdownGuest()
            retry_count = 0
            while True:
                retry_count += 1
                if retry_count < const.SHUTDOWN_RETRY:
                    if ovsvapp['runtime.powerState'] == 'poweredOff':
                        LOG.info("Successfully shutdown '{}'"
                                 .format(ovsvapp_name))
                        return
                    delay = (const.SHUTDOWN_RETRY_DELAY * retry_count)
                    LOG.info("Waiting for '{}' to shutdown. Retrying again in "
                             "{} seconds... {}".format(ovsvapp_name, delay,
                                                       retry_count))
                    time.sleep(delay)
                else:
                    raise Exception(_("Timed out while "
                                      "shutting down guest OS"))
        except Exception as e:
            LOG.exception(ovsvapp_name=ovsvapp_name, reason=e)
            LOG.info("Initiating a hard shutdown ...")
            self._poweroff_ovsvapp_task(ovsvapp)

    def _get_conf_ip(self, vm_obj):
        vm_config = util.get_vmconfig_input(self.inputs, constants.OVSVAPP_KEY)
        conf_pg = util.get_conf_pg(self.inputs, vm_config)
        conf_ip, __ = util.VMwareUtils.get_conf_network_details(
            vm_obj, conf_pg.get('name'))
        return conf_ip

    def _remove_affinity_rule(self, vms):
        rule_infos = self.cluster['obj'].configuration.rule
        groupspec = list()
        rulespec = list()
        if rule_infos:
            # Rules are there and can be any rule.
            cluster_spec_ex = vim.cluster.ConfigSpecEx()
            for vm in vms:
                key = None
                host = vm['runtime.host']
                host_group_spec = vim.cluster.GroupSpec()
                vm_group_spec = vim.cluster.GroupSpec()
                host_group_spec.operation = 'remove'
                host_group_spec.removeKey = host.name
                vm_group_spec.operation = 'remove'
                vm_group_spec.removeKey = vm['name']
                groupspec.append(host_group_spec)
                groupspec.append(vm_group_spec)
                rules_spec = vim.cluster.RuleSpec()
                for rule in rule_infos:
                    # Find out the rule with ovsvapp name and get the key
                    if rule.name == vm['name']:
                        key = rule.key
                        break
                if key:
                    # Create the remove spec for only those vms which exists
                    rules_spec.operation = 'remove'
                    rules_spec.removeKey = key
                    rulespec.append(rules_spec)
            cluster_spec_ex.groupSpec = groupspec
            cluster_spec_ex.rulesSpec = rulespec
            task = self.cluster['obj'].ReconfigureComputeResource_Task(
                cluster_spec_ex, True)
            util.VMwareUtils.wait_for_task(task, self.si)

    def _delete_ovsvapps_task(self, ovsvapp):
        ovsvapp_name = ovsvapp['name']
        try:
            conf_ip = self._get_conf_ip(ovsvapp['obj'])
            if not conf_ip:
                LOG.error("Deleting '{}' but couldn't find the conf IP in the "
                          "VM.".format(ovsvapp_name))
            if ovsvapp['runtime.powerState'] != 'poweredOff':
                self._poweroff_ovsvapp_task(ovsvapp)
            destroy_task = ovsvapp['obj'].Destroy()
            util.VMwareUtils.wait_for_task(destroy_task, self.si)
            LOG.info("Deleted '%s'" % ovsvapp_name)
            return conf_ip
        except Exception as e:
            if isinstance(e, vim.fault.InvalidState):
                msg = (_("The ESXi host or the VM is not in valid state "
                       "to destroy '{}' ").format(ovsvapp_name))
                LOG.exception(msg)
                raise OVSvAppException(msg)
            else:
                LOG.exception(e)
                raise OVSvAppException(ovsvapp_name=ovsvapp_name, reason=e)

    def _remove_cluster_vni_allocation(self):
        cluster = self.cluster
        vcenter_id = self.content.about.instanceUuid
        cluster_path = "/".join(
            [self.dc_name, OVSvAppUtil.get_cluster_inventory_path(
                cluster['obj'], cluster['name'], False)])
        try:
            eon_env = OVSvAppUtil.get_eon_env(self.inputs.get('neutron'))
            cmd = ("neutron ovsvapp-cluster-update --vcenter_id %s "
                   "--clusters %s" % (vcenter_id, cluster_path))
            command = cmd.split(" ")
            OVSvAppUtil.exec_subprocess(command, eon_env)
        except Exception as e:
            LOG.exception(e)
            raise OVSvAppException(_("Error occurred while invoking CLI "
                                   "'{}'").format(cmd))

    def unimport_cluster(self):
        try:
            vm_map = OVSvAppUtil.get_ovsvapps(
                self.content, self.vm_folder, self.cluster)
            if vm_map:
                ovsvapps = vm_map.values()
                delete_jobs = [(ovsvapp) for ovsvapp in zip(ovsvapps)]
                released_ips = OVSvAppUtil.exec_multiprocessing(
                    self._delete_ovsvapps_task, delete_jobs)
                util.SharedIPAllocator.release_ips(released_ips)
                self._remove_affinity_rule(ovsvapps)
                LOG.info("Released IPs: {}".format(released_ips))
            self._remove_cluster_vni_allocation()
            return True
        except Exception as e:
            LOG.exception(e)
            return False

    def deactivate_cluster(self):
        try:
            vm_map = OVSvAppUtil.get_ovsvapps(
                self.content, self.vm_folder, self.cluster)
            if vm_map:
                ovsvapps = vm_map.values()
                args = [(ovsvapp) for ovsvapp in zip(ovsvapps)]
                OVSvAppUtil.exec_multiprocessing(
                    self._shutdown_ovsvapp_task, args)
            return True
        except Exception as e:
            LOG.exception(e)
            return False
