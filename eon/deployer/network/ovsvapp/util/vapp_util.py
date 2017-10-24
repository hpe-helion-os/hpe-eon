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

import subprocess

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from pyVmomi import vim
from pyVmomi import vmodl

from keystoneclient.v3 import client

from eon.common import exception
import eon.common.log as logging
from eon.deployer.network.ovsvapp.util import vapp_constants as const
from eon.deployer.network.ovsvapp.util.status_messages import get_status
from eon.deployer.util import VMwareUtils


LOG = logging.getLogger(__name__)


class OVSvAppUtil:

    @staticmethod
    def get_ovsvapps(content, vm_folder, cluster):
        ovsvapps = dict()
        all_vms = VMwareUtils.get_all_vms(content, cluster['resourcePool'])
        for vm in all_vms:
            if vm['name'].startswith(const.OVS_VAPP_PREFIX):
                if const.OVS_VAPP_IDENTIFIER in vm['config.annotation']:
                    ovsvapps[vm['runtime.host']] = vm
        return ovsvapps

    @staticmethod
    def get_active_hosts(content, vm_folder, vapp_hosts, cluster):
        """
        Filter out active hosts from clusters
        @return: List of active hosts.
        """
        hosts = []
        all_hosts = VMwareUtils.get_all_hosts(content, cluster)
        host_power_state = {'poweredOn': 'poweredOn',
                            'poweredOff': 'poweredOff',
                            'standBy': 'standBy',
                            'unknown': 'unknown',
                            'maintenanceMode': 'Maintenance Mode'}
        for host in all_hosts:
            if host['obj'] in vapp_hosts:
                continue
            host['cluster'] = cluster
            host_name = host['name']
            power_state = host['summary.runtime.powerState']
            maintenance_mode = host['summary.runtime.inMaintenanceMode']
            host_api_version = host['config.product.apiVersion']
            is_new_host = False
            if vapp_hosts:
                is_new_host = True
                if not maintenance_mode:
                    LOG.error("Cannot add host '%s' which is not in "
                              "maintenance mode" % host['name'])
                    continue
                else:
                    maintenance_mode = False
            if power_state == 'poweredOn' and not maintenance_mode:
                if host_api_version >= const.MIN_SUPPORTED_VERSION:
                    shared_storage = VMwareUtils.get_shared_datastore(
                        host, is_new_host)
                    if shared_storage:
                        host['shared_storage'] = shared_storage
                        hosts.append(host)
                    else:
                        msg = get_status(322, status='failed',
                                         host=host['name'])
                        LOG.error(msg)
                        raise exception.OVSvAppException(msg)
                else:
                    LOG.error("Esxi host '%s' version is '%s' which is"
                              " not supported. Minimum supported "
                              "version is '%s' . Excluding this host "
                              "from OVSvApp installation" %
                              (host_name, host_api_version,
                               const.MIN_SUPPORTED_VERSION))
                    msg = get_status(309, status='failed',
                                     host=host['name'])
                    raise exception.OVSvAppException(msg)
            else:
                if power_state == 'poweredOn':
                    if maintenance_mode:
                        state = host_power_state['maintenanceMode']
                else:
                    state = host_power_state[power_state]
                LOG.warn("Esxi host '%s' is in '%s' state. Excluding this "
                         "host from OVSvApp installation" %
                         (host_name, state))
        return hosts

    @staticmethod
    def exec_multiprocessing(method, args):
        results = []
        with ThreadPoolExecutor(max_workers=const.WORKERS) as executor:
            futures = {executor.submit(method, *arg): arg for arg in args}
            for future in as_completed(futures):
                results.append(future.result())
        return results

    @staticmethod
    def _get_folder(content, host_folder, folder_name):
        container = content.viewManager.CreateContainerView(
            host_folder, [vim.Folder], True)
        folder = None
        for view in container.view:
            if view.name == folder_name:
                folder = view
                break
        return folder

    @staticmethod
    def create_host_folder(content, hosts, host_folder):
        for host in hosts:
            folder_name = str(host['cluster'].get('mo_id'))
            folder = OVSvAppUtil._get_folder(content, host_folder, folder_name)
            if not folder:
                folder = host_folder.CreateFolder(folder_name)
            host['folder'] = folder

    @staticmethod
    def move_hosts_in_to_folder(si, hosts):
        host_map = {}
        for host in hosts:
            folder = host['folder']
            host_map.setdefault(folder, [])
            host_map[folder].append(host)
        for folder in host_map.keys():
            host_objs = [host['obj'] for host in host_map.get(folder)]
            task = folder.MoveIntoFolder_Task(host_objs)
            VMwareUtils.wait_for_task(task, si)
            LOG.debug("Successfully moved the hosts in folder '%s'" %
                      folder.name)
        for host in hosts:
            task = host['obj'].ExitMaintenanceMode_Task(timeout=1800)
            VMwareUtils.wait_for_task(task, si)
            LOG.debug("Host '%s' is out of maintenance mode" % host['name'])

    @staticmethod
    def enter_maintenance_mode(host, si):
        try:
            task = host['obj'].EnterMaintenanceMode_Task(
                timeout=300, evacuatePoweredOffVms=False)
            VMwareUtils.wait_for_task(task, si)
        except Exception as e:
            LOG.exception("Caught exception %s" % e)

    @staticmethod
    def destroy_failed_commissioned_vapps(host, si):
        vms = host['obj'].vm
        LOG.info("Destroying OVSvApps to enter maintenance mode")
        for vm in vms:
            if const.OVS_VAPP_IDENTIFIER in vm.config.annotation:
                if vm.runtime.powerState != 'poweredOff':
                    shutdown_task = vm.PowerOff()
                    VMwareUtils.wait_for_task(shutdown_task, si)
                    destroy_task = vm.Destroy()
                    VMwareUtils.wait_for_task(destroy_task, si)

    @staticmethod
    def move_host_back_to_cluster(si, host, cluster, prep_folder, err=False):
        if err:
            OVSvAppUtil.destroy_failed_commissioned_vapps(host, si)
            OVSvAppUtil.enter_maintenance_mode(host, si)
        prep_folder_name = prep_folder.name
        move_task = cluster['obj'].MoveInto_Task([host['obj']])
        VMwareUtils.wait_for_task(move_task, si)
        LOG.debug("Successfully moved host '%s' to cluster '%s'" %
                  (host['name'], cluster['name']))
        if not prep_folder.childEntity:
            del_task = prep_folder.Destroy_Task()
            VMwareUtils.wait_for_task(del_task, si)
            LOG.debug("Deleted folder '%s'" % prep_folder_name)

    @staticmethod
    def get_host_parent(item, parent_type):
        if not isinstance(item.parent, parent_type):
            parent = OVSvAppUtil.get_host_parent(item.parent, parent_type)
            if parent is not None:
                return parent
        else:
            return item.parent

    @staticmethod
    def get_cluster_inventory_path(item, cluster_path, shell=True):
        if isinstance(item.parent, vim.Folder):
            if shell:
                cluster_path = "\\\\/".join([item.parent.name, cluster_path])
            else:
                cluster_path = "/".join([item.parent.name, cluster_path])
            return OVSvAppUtil.get_cluster_inventory_path(
                item.parent, cluster_path, shell)
        else:
            return cluster_path

    @staticmethod
    def _get_keystoneclient(neutron):
        try:
            keystone = client.Client(
                username=neutron['admin_username'],
                password=neutron['admin_password'],
                tenant_name=neutron['admin_tenant_name'],
                auth_url=neutron['admin_auth_url'])
            return keystone
        except Exception as e:
            msg = ("An exception occurred while retrieving the Keystone "
                   "Client")
            LOG.exception(e)
            LOG.exception(msg)
            raise exception.OVSvAppException(msg)

    @staticmethod
    def get_eon_env(neutron):
        keystone = OVSvAppUtil._get_keystoneclient(neutron)
        token = keystone.service_catalog.get_token()
        if not token:
            msg = "Couldn't retrieve the Keystone token."
            LOG.exception(msg)
            raise exception.OVSvAppException(msg)
        my_env = dict()
        my_env['OS_USER_DOMAIN_NAME'] = "Default"
        my_env['OS_PROJECT_DOMAIN_NAME'] = "Default"
        my_env['OS_USERNAME'] = neutron['admin_username']
        my_env['OS_PASSWORD'] = neutron['admin_password']
        my_env['OS_PROJECT_NAME'] = neutron['admin_tenant_name']
        my_env['OS_AUTH_URL'] = neutron['admin_auth_url']
        my_env['OS_URL'] = neutron['endpoint_url']
        my_env['OS_TOKEN'] = token.get('id')
        return my_env

    @staticmethod
    def exec_subprocess(command):
        output = subprocess.Popen(
            command, stdout=subprocess.PIPE).communicate()[0]
        LOG.info(output)
        return output

    @staticmethod
    def disable_ha_on_ovsvapp(si, vm, cluster, host):
        try:
            ovs_vm_name = vm.name
            cluster_spec_ex = vim.cluster.ConfigSpecEx()
            if cluster['configuration.dasConfig.enabled']:
                settings = []
                config_spec = vim.cluster.DasVmConfigSpec()
                config_spec.operation = \
                    vim.option.ArrayUpdateSpec.Operation.add
                config_info = vim.cluster.DasVmConfigInfo()
                config_info.key = vm
                config_info.powerOffOnIsolation = False
                config_info.restartPriority = \
                    vim.cluster.DasVmConfigInfo.Priority.disabled
                vm_settings = vim.cluster.DasVmSettings()
                vm_settings.restartPriority = \
                    vim.cluster.DasVmSettings.RestartPriority.disabled
                monitor = vim.cluster.VmToolsMonitoringSettings()
                monitor.vmMonitoring = \
                    vim.cluster.DasConfigInfo.VmMonitoringState. \
                    vmMonitoringDisabled
                monitor.clusterSettings = False
                vm_settings.vmToolsMonitoringSettings = monitor
                config_info.dasSettings = vm_settings
                config_spec.info = config_info
                settings.append(config_spec)
                cluster_spec_ex.dasVmConfigSpec = settings
            else:
                LOG.warn("HA is not enabled on cluster %s . Couldn't disable "
                         "HA for %s" % (cluster['name'], ovs_vm_name))
            if cluster['configuration.drsConfig.enabled']:
                drs_config_spec = vim.cluster.DrsVmConfigSpec()
                drs_config_spec.operation = \
                    vim.option.ArrayUpdateSpec.Operation.add
                drs_vm_config_info = vim.cluster.DrsVmConfigInfo()
                drs_vm_config_info.key = vm
                drs_vm_config_info.enabled = False
                drs_vm_config_info.behavior = \
                    vim.cluster.DrsConfigInfo.DrsBehavior.manual
                drs_config_spec.info = drs_vm_config_info
                cluster_spec_ex.drsVmConfigSpec = [drs_config_spec]
                host_group_spec = vim.cluster.GroupSpec()
                host_group = vim.cluster.HostGroup()
                vm_group_spec = vim.cluster.GroupSpec()
                vm_group = vim.cluster.VmGroup()
                host_group_spec.operation = 'add'
                host_group.host = [host['obj']]
                vm_group_spec.operation = 'add'
                vm_group.vm = [vm]
                host_group.name = host['name']
                host_group_spec.info = host_group
                vm_group.name = ovs_vm_name
                vm_group_spec.info = vm_group
                cluster_spec_ex.groupSpec = [host_group_spec, vm_group_spec]
                rules_spec = vim.cluster.RuleSpec()
                rules_spec.operation = 'add'
                host_vm_info = vim.cluster.VmHostRuleInfo()
                host_vm_info.affineHostGroupName = host['name']
                host_vm_info.vmGroupName = ovs_vm_name
                host_vm_info.enabled = True
                host_vm_info.mandatory = True
                host_vm_info.name = ovs_vm_name
                rules_spec.info = host_vm_info
                cluster_spec_ex.rulesSpec = [rules_spec]
            else:
                LOG.warn("DRS is not enabled on cluster %s . Couldn't"
                         " disable DRS for %s" % (cluster['name'],
                                                  ovs_vm_name))
            LOG.info("Disabling HA & DRS for %s" % ovs_vm_name)
            task = cluster['obj'].ReconfigureComputeResource_Task(
                cluster_spec_ex, True)
            VMwareUtils.wait_for_task(task, si)
            LOG.info("Successfully disabled HA & DRS for %s" % ovs_vm_name)
        except vmodl.MethodFault as e:
            # Vmware related exception
            msg = e.msg
            if(msg.startswith("The setting of vmConfig is invalid")):
                LOG.warn("Couldn't disable HA & DRS for %s" % ovs_vm_name)
                LOG.warn("Please turn off and turn on HA & DRS from Cluster "
                         "settings.")
            else:
                LOG.error("Caught VMware API fault: %s" % e.msg)
                return
        except Exception as e:
            # Unknown Exception
            LOG.error("Caught exception: %s" % e)
            return
