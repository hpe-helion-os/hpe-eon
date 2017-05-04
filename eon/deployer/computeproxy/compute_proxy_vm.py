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

import time

from pyVmomi import vim
from pyVmomi import vmodl

from eon.common import exception
from eon.common import log
from eon.deployer import constants
from eon.deployer import upload_ova
from eon.deployer import util

from oslo_config import cfg

CONF = cfg.CONF

LOG = log.getLogger(__name__)

SHUTDOWN_RETRY_DELAY = 8


def get_one_active_host_for_cluster(content, cluster):
    """
    Returns the active host in the given cluster
    :param cluster: cluster object
    :return: host object
    """
    host_list = util.VMwareUtils.get_all_hosts(content, cluster)
    for host in host_list:
        if (host['summary.runtime.powerState'] == 'poweredOn' and
                not host['summary.runtime.inMaintenanceMode']):
            return host


def get_vm_location_details(content, dc_name, cluster_moid):
    """
    Returns the location details of compute proxy vm

    Parameters
    ----------
    content : ServiceContent object
    dc_name : str
    cluster_moid : VMware Managed Object ID

    Returns
    -------
    vm_loc_details : dict of cluster, host, datastore and datacenter details
    """
    datacenter = util.VMwareUtils.get_data_center(content, dc_name)
    cluster = util.VMwareUtils.get_cluster(
        content, datacenter['hostFolder'], cluster_moid)
    host = get_one_active_host_for_cluster(content, cluster)
    host['cluster'] = cluster
    if not host:
        raise exception.ProxyNoHostFound(cluster_name=cluster['name'],
                                         datacenter_name=datacenter['name'])
    LOG.debug("Using the host (%s) of the cluster (%s)"
              % (host['name'], cluster['name']))

    datastore_obj = util.VMwareUtils.get_shared_datastore(host)
    if not datastore_obj:
        raise exception.ProxyNoValidDatastoreFound(
            cluster_name=cluster['name'])
    vm_loc_details = {"cluster": cluster,
                      "host": host,
                      "datastore": datastore_obj,
                      "datacenter": datacenter}
    return vm_loc_details


def shut_down_vm(vm, si):
    """
    To shut down compute proxy node

    Parameters
    ----------
    vm : VirtualMachine object
    si : ServiceInstance Object
    """
    try:
        vm.ShutdownGuest()
        retry_count = 0
        while True:
            delay = constants.TASK_WAIT_DELAY
            retry_count += 1
            if retry_count < SHUTDOWN_RETRY_DELAY:
                if (vm.runtime.powerState ==
                        vim.VirtualMachinePowerState.poweredOff):
                    LOG.info("VM (%s) shutdown completed" % vm.name)
                    return True
                time.sleep(delay * retry_count)
            else:
                msg = (_("Timed out while shutting down {}").format(vm.name))
                log_msg = (("Timed out while shutting"
                            " down {}").format(vm.name))
                LOG.exception(log_msg)
                raise exception.ProxyException(msg)
    except Exception as e:
        LOG.exception(_('Failed to shutdown VM (%s) due to %s. '
                      'Initiate hard power off') % (vm.name, e))
    power_off_vm(vm, si)


def power_off_vm(vm, si):
    """
    To power off compute proxy node

    Parameters
    ----------
    vm : VirtualMachine object
    si : ServiceInstance Object
    """
    try:
        task = vm.PowerOff()
        status = util.VMwareUtils.wait_for_task(
            task, si, actionName='powerOff')
        if status:
            LOG.error("Failed to powerOff VM (%s) due to (%s)"
                      % (vm.name, status))
            raise exception.ProxyPowerOffFailure(vm_name=vm.name,
                                                 reason=status)
        LOG.info("VM (%s) power off completed" % vm.name)
        return True
    except Exception as e:
        LOG.exception(e)
        raise exception.ProxyPowerOffFailure(vm_name=vm.name, reason=e)


def delete_vm(vm, si):
    """
    To delete compute proxy node

    Parameters
    ----------
    vm : VirtualMachine object
    si : ServiceInstance Object
    """
    try:
        vm_name = vm.name
        task = vm.Destroy()
        status = util.VMwareUtils.wait_for_task(
            task, si, actionName='destroyVM')
        LOG.info('status of destroyVM')
        LOG.info(status)
        if status:
            err_msg = "Failed to delete VM (%s)" % vm_name
            LOG.error(err_msg)
            raise exception.ProxyDeleteFailure(vm_name=vm_name, reason=status)
        else:
            LOG.info("VM (%s) deletion completed" % vm_name)
    except Exception as e:
        LOG.exception(e)
        raise exception.ProxyDeleteFailure(vm_name=vm.name, reason=e)


def create_shell_vm(session, vm_name, data):
    """
    Manage and collect data for cloning and configuring VM from template
    """
    LOG.info("Invoked create compute proxy vm task")
    cleanup = True
    conf_network = {}
    conf_ip = None
    try:
        proxy_info = dict()
        vcenter_details = data.get("vcenter_configuration")
        dc_name = vcenter_details.get("datacenter")
        cluster_moid = vcenter_details.get("cluster_moid")
        content = session.get('content')

        vm_loc_details = get_vm_location_details(
            content, dc_name, cluster_moid)
        datacenter = vm_loc_details.get('datacenter')
        cluster = vm_loc_details.get('cluster')
        host = vm_loc_details.get('host')
        datastore = vm_loc_details.get('datastore')

        vm = util.VMwareUtils.get_vm(session, vm_name, datacenter['vmFolder'])
        if vm:
            LOG.info("VM (%s) already present. Skipping the computeproxy"
                     " installation" % vm_name)
            cleanup = False
            return dict()

        vm_config = util.get_vmconfig_input(
            data, constants.PROXY_KEY,
            net_driver=CONF.network.esx_network_driver)

        ova_manager = upload_ova.OVAUploadManager(session,
                                        vm_config['template_name'],
                                        vm_config['template_location'],
                                        datacenter, cluster, host,
                                        datastore)
        template = ova_manager.upload_ova()

        devices = util.VMwareUtils.get_virtual_devices(
            datacenter['networkFolder'], cluster['obj'], host['obj'],
            vm_config.get('nics'))
        vmconf = util.VMwareUtils.get_vm_config(vm_config, devices)
        location = util.VMwareUtils.get_relocation_spec(
            host['obj'], cluster['resourcePool'], datastore)
        cloned_vm = util.VMwareUtils.clone_vm(
            session.get('si'), template['obj'], location, vm_name,
            datacenter['vmFolder'], vmconf)
        if isinstance(cloned_vm, vim.VirtualMachine):
            LOG.info("vCenter proxy VM (%s) created on host (%s)"
                     % (vm_name, host['name']))
            conf_network = util.get_conf_pg(data, vm_config)
            ip_config = data.get('esx_conf_net')
            conf_ip = util.SharedIPAllocator().get_ips(
                ip_config['cidr'], ip_config['start_ip'], ip_config['end_ip'],
                ip_config['gateway'], 1)[0]
            util.ServiceVMCustomizer(data).customize_service_vm(
                content, cloned_vm, host['obj'], conf_network,
                conf_ip, vm_config.get('nics'))
            proxy_info = get_shell_vm_info(
                session, vm_name, conf_network.get('name'), conf_ip)
            proxy_info['server_role'] = vm_config.get('server_role')
            cleanup = False
            LOG.info("Finished create tasks successfully")
            return proxy_info
        else:
            err_msg = (_("Error occurred while cloning '{}'").format(vm_name))
            log_err_msg = (("Error occurred while"
                            " cloning '{}'").format(vm_name))
            LOG.error(log_err_msg)
            raise exception.ProxyException(err_msg)
    except vmodl.MethodFault as e:
        msg = _("Caught VMware API fault: (%s)") % e
        log_msg = ("Caught VMware API fault: (%s)") % e
        LOG.error(log_msg)
        raise exception.ProxyException(msg)
    except Exception as e:
        LOG.exception(e)
        raise exception.ProxyException(e)
    finally:
        if cleanup:
            if conf_ip:
                util.SharedIPAllocator.release_ips([conf_ip])
            delete_shell_vm(session, vm_name, conf_network.get('name'),
                            force=True)


def delete_shell_vm(session, vm_name, conf_pg_name, force=False):
    """
    To delete the compute proxy node from the vCenter
    """
    LOG.info("Invoked delete proxy vm from the vCenter")
    try:
        content = session.get('content')
        vm = content.rootFolder.find_by_name(vm_name)
        if not vm:
            err_msg = "No VM (%s) found in vCenter" % vm_name
            LOG.error(err_msg)
            return
        ip, __ = util.VMwareUtils.get_conf_network_details(
            vm, conf_pg_name)
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            LOG.info("VM (%s) powered on. Initiate Shut down." % vm_name)
            force = shut_down_vm(vm, session['si'])
        else:
            LOG.info("VM (%s) powered off" % vm_name)
            force = True

        if force:
            LOG.info("Going to delete VM")
            delete_vm(vm, session['si'])
            # Release the IP from ip_catalog.json
            util.SharedIPAllocator().release_ips([ip])
    except vmodl.MethodFault as e:
        msg = _("Caught VMware API fault: (%s)") % e
        log_msg = ("Caught VMware API fault: (%s)") % e
        LOG.error(log_msg)
        raise exception.ProxyException(msg)
    LOG.info("Finished delete vm successfully")


def get_shell_vm_info(session, vm_name, conf_pg_name,
                      conf_ip_static=None):
    """
    Returns the ipaddress and macaddress of the deployer of management
     network of the compute proxy node
    :param session:
    :param vm_name:
    :return:
    """
    LOG.info("Get the details of the shell VM (%s)" % vm_name)
    try:
        proxy_details = dict()
        content = session.get('content')
        vm = content.rootFolder.find_by_name(vm_name)
        if not vm:
            LOG.error("No VM (%s) found in vCenter" % vm_name)
            return dict()
        pxe_ip, pxe_mac = util.VMwareUtils.get_conf_ip_and_mac(
            vm, conf_pg_name, conf_ip_static)
        if not all([pxe_ip, pxe_mac]):
            return dict()
        proxy_details = {"name": vm_name,
                         "pxe-ip-addr": pxe_ip,
                         "pxe-mac-addr": pxe_mac}
        LOG.info("Returning (%s) compute proxy details: (%s)"
                 % (vm_name, proxy_details))
        return proxy_details

    except vmodl.MethodFault as e:
        msg = _("Caught VMware API fault: (%s)") % e
        log_msg = ("Caught VMware API fault: (%s)") % e
        LOG.error(log_msg)
        raise exception.ProxyException(msg)
    except Exception as e:
        msg = _("Caught exception: (%s)") % e
        log_msg = ("Caught exception: (%s)") % e
        LOG.error(log_msg)
        raise exception.ProxyException(msg)
