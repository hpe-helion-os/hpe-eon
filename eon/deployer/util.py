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

import atexit
import base64
import json
import os
import ssl
import threading
import time

import netaddr

from pyVim.connect import Disconnect
from pyVim.connect import SmartConnect
from pyVmomi import vim
from pyVmomi import vmodl

import requests
import requests.packages.urllib3 as urllib3

from eon import deployer
from eon.common import exception
import eon.common.log as logging
from eon.deployer import constants

LOG = logging.getLogger(__name__)


class SharedIPAllocator:
    _lock = threading.RLock()

    @staticmethod
    def _get_ip_list(cidr, start_ip, end_ip, gateway):
        ips = [str(ip) for ip in list(netaddr.IPNetwork(cidr))]
        # Remove gateway
        if gateway in ips:
            ips.remove(gateway)
        if all([start_ip, end_ip]):
            ips = ips[ips.index(start_ip): ips.index(end_ip) + 1]
        else:
            # chop out the first and last ips
            ips = ips[1: -1]
        return ips

    @staticmethod
    def get_net_mask(cidr):
        return str(netaddr.IPNetwork(cidr).netmask)

    @staticmethod
    def get_ips(cidr, start_ip, end_ip, gateway, num_ips):
        with SharedIPAllocator._lock:
            ip_list = SharedIPAllocator._get_ip_list(
                cidr, start_ip, end_ip, gateway)
            if len(ip_list) < num_ips:
                msg = _("Requested CIDR '%s' has less number of IPs than the "
                       "number of IPs requested")
                raise exception.InsufficientIPException(msg)
            ip_catalog = load_json_data(constants.IP_CATALOG_FILE)
            used_ips = ip_catalog
            unused_ips = [ip for ip in ip_list if ip not in used_ips]
            requested_ips = unused_ips[:num_ips]
            SharedIPAllocator._store_ips(requested_ips)
        if len(requested_ips) < num_ips:
            msg = _("Couldn't serve requested number of IPs because of "
                   "duplicate IPs %s" % used_ips)
            raise exception.InsufficientIPException(msg)
        return requested_ips

    @staticmethod
    def _store_ips(ips):
        ip_catalog = update_json_data(ips, constants.IP_CATALOG_FILE)
        dump_json_data(ip_catalog, constants.IP_CATALOG_FILE)

    @staticmethod
    def release_ips(ips):
        with SharedIPAllocator._lock:
            ip_catalog = None
            if os.path.isfile(constants.IP_CATALOG_FILE):
                ip_catalog = load_json_data(constants.IP_CATALOG_FILE)
            if ip_catalog:
                try:
                    [ip_catalog.remove(ip) for ip in ips]
                    LOG.info("Released IP '%s'" % ip)
                    dump_json_data(ip_catalog, constants.IP_CATALOG_FILE)
                except ValueError:
                    # No need to handle anything
                    pass


class VMwareUtils:

    @staticmethod
    def get_vcenter_session(vcenter_host, vcenter_port, vcenter_user,
                            vcenter_pwd):
        """
        Connect to Vcenter Server with specified credentials
        @return: Service Instance
        """
        try:
            LOG.info("Trying to connect to vCenter Server {} ...".
                     format(vcenter_host))
            urllib3.disable_warnings()
            si = None
            context = None
            if hasattr(ssl, 'SSLContext'):
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                context.verify_mode = ssl.CERT_NONE
            if context:
                # Python >= 2.7.9
                si = SmartConnect(host=vcenter_host,
                                  port=int(vcenter_port),
                                  user=vcenter_user,
                                  pwd=vcenter_pwd,
                                  sslContext=context)
            else:
                # Python >= 2.7.7
                si = SmartConnect(host=vcenter_host,
                                  port=int(vcenter_port),
                                  user=vcenter_user,
                                  pwd=vcenter_pwd)
            atexit.register(Disconnect, si)
            LOG.info("Connected to vCenter Server {}".format(vcenter_host))
            return si
        except vmodl.MethodFault as e:
            msg = _("Couldn't connect the vCenter "
                    "server because of VMware fault")
            LOG.exception(e)
            raise exception.VcenterConnectionException(msg)
        except Exception as e:
            LOG.exception(e)
            raise exception.VcenterConnectionException()

    @staticmethod
    def wait_for_task(task, si, actionName='job', hideResult=False):
        property_collector = si.content.propertyCollector
        task_list = [str(task)]
        obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)]
        property_spec = vmodl.query.PropertyCollector. \
            PropertySpec(type=vim.Task, pathSet=[], all=True)
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_specs
        filter_spec.propSet = [property_spec]
        pcfilter = property_collector.CreateFilter(filter_spec, True)
        try:
            version, state = None, None
            while len(task_list):
                update = property_collector.WaitForUpdates(version)
                for filter_set in update.filterSet:
                    for obj_set in filter_set.objectSet:
                        task = obj_set.obj
                        for change in obj_set.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue
                            if not str(task) in task_list:
                                continue
                            if state == vim.TaskInfo.State.success:
                                # Remove task from taskList
                                task_list.remove(str(task))
                                return task.info.result
                            elif state == vim.TaskInfo.State.error:
                                return task.info.error
                version = update.version
        finally:
            if pcfilter:
                pcfilter.Destroy()

    @staticmethod
    def wait_for_vmware_tools(vm, host):
        """
        Wait for the guest OS to boot up and VMware tools
        to be ready.
        """
        retry_count = 0
        while True:
            delay = constants.TASK_WAIT_DELAY
            retry_count += 1
            if retry_count < constants.VM_TOOLS_RETRY_COUNT:
                current_state = vm.guest.toolsStatus
                if current_state == 'toolsOk' or current_state == 'toolsOld':
                    return
                time.sleep(delay * retry_count)
            else:
                msg = (_("Timed out while waiting for VMware Tools to be "
                       "ready. This means either VMware Tools are not "
                       "installed on the VM '{}' or the guest OS may took "
                       "more than 5 mins to boot up").format(vm.name))
                LOG.exception(msg)
                raise exception.VMwareToolsNotRunning(msg)

    @staticmethod
    def get_view_ref(content, obj_type, vim_type):
        view_ref = content.viewManager.CreateContainerView(
            container=obj_type,
            type=vim_type,
            recursive=True)
        return view_ref

    @staticmethod
    def get_list_view_ref(content, entity_obj):
        return content.viewManager.CreateListView(obj=[entity_obj])

    @staticmethod
    def collect_properties(content, view_ref, lazy_type_obj,
                           path_set=None, include_mors=False):
        collector = content.propertyCollector
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view_ref
        obj_spec.skip = True
        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.name = 'traverseEntities'
        traversal_spec.path = 'view'
        traversal_spec.skip = False
        traversal_spec.type = view_ref.__class__
        obj_spec.selectSet = [traversal_spec]
        property_spec = vmodl.query.PropertyCollector.PropertySpec()
        property_spec.type = lazy_type_obj
        if not path_set:
            property_spec.all = True
        property_spec.pathSet = path_set
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [property_spec]
        props = collector.RetrieveContents([filter_spec])
        data = []
        for obj in props:
            properties = {}
            for prop in obj.propSet:
                properties[prop.name] = prop.val
            if include_mors:
                properties['obj'] = obj.obj
                properties['mo_id'] = properties['obj']._moId
            data.append(properties)
        return data

    @staticmethod
    def get_all_vms(content, container):
        all_vms = []
        vm_view = VMwareUtils.get_view_ref(
            content, container, [vim.VirtualMachine])
        vm_prop = constants.VM_PROPS
        all_vms += VMwareUtils.collect_properties(
            content, vm_view, vim.VirtualMachine, vm_prop, True)
        return all_vms

    @staticmethod
    def get_all_hosts(content, cluster):
        host_view = VMwareUtils.get_view_ref(
            content, cluster['obj'], [vim.HostSystem])
        host_prop = ['name', 'parent', 'network', 'datastore',
                     'summary.runtime.powerState', 'vm',
                     'summary.runtime.inMaintenanceMode',
                     'config.product.apiVersion',
                     'config.network.pnic',
                     'config.network.vswitch',
                     'config.network.proxySwitch']
        host_refs = VMwareUtils.collect_properties(
            content, host_view, vim.HostSystem, host_prop, True)
        return host_refs

    @staticmethod
    def get_data_center(content, dc_name):
        dc_view = VMwareUtils.get_view_ref(
            content, content.rootFolder, [vim.Datacenter])
        dc_prop = ['name', 'vmFolder', 'hostFolder', 'networkFolder']
        dc_refs = VMwareUtils.collect_properties(
            content, dc_view, vim.Datacenter, dc_prop, True)
        for datacenter in dc_refs:
            if datacenter['name'] == dc_name:
                return datacenter
        msg = (_("Couldn't find the datacenter '{}' with the provided name")
               .format(dc_name))
        LOG.error(msg)
        raise exception.DatacenterNotfoundError(msg)

    @staticmethod
    def get_cluster(content, host_folder, cluster_moid=None,
                    cluster_name=None):
        cluster_view = VMwareUtils.get_view_ref(
            content, host_folder, [vim.ClusterComputeResource])
        cluster_prop = ['name', 'resourcePool', 'host', 'datastore',
                        'network', 'configuration.dasConfig.enabled',
                        'configuration.drsConfig.enabled']
        cluster_refs = VMwareUtils.collect_properties(
            content, cluster_view, vim.ClusterComputeResource,
            cluster_prop, True)
        for cluster in cluster_refs:
            if not cluster_name:
                if cluster['mo_id'] == cluster_moid:
                    return cluster
            else:
                # HLM playbook call will hit this where they don't have moid
                if cluster['name'] == cluster_name:
                    return cluster
        msg = (_("Couldn't find the cluster '{}' with the provided id")
               .format(cluster_moid))
        LOG.error(msg)
        raise exception.ClusterNotfoundError(msg)

    @staticmethod
    def get_vm(session, vm_name, vm_folder=None):
        content = session['content']
        if not vm_folder:
            vm_folder = content.rootFolder
        all_vm_refs = VMwareUtils.get_all_vms(content, vm_folder)
        for vm in all_vm_refs:
            if vm['name'] == vm_name:
                return vm

    @staticmethod
    def get_template(session, vm_name, vm_folder=None):
        template = VMwareUtils.get_vm(session, vm_name, vm_folder)
        if template:
            return template
        msg = ("Couldn't find the template '{}' in the provided datacenter"
               .format(vm_name))
        LOG.warn(msg)

    @staticmethod
    def get_template_ref(content, lease, props=[]):
        """
        Using Views
        """
        if not props:
            props = constants.VM_PROPS

        template_view = (
            VMwareUtils.get_list_view_ref(content,
                                          lease.info.entity))
        vm_ref = VMwareUtils.collect_properties(content, template_view,
                                                vim.VirtualMachine, props,
                                                include_mors=True)
        template_view.DestroyView()
        return vm_ref[0]

    @staticmethod
    def _get_max_capacity_datastore(datastores):
        ds_available_space = {ds.summary.freeSpace: ds for ds in datastores}
        # Get the maximum available free disk space
        max_free_space = max(ds_available_space, key=long)
        # Return the datastore with maximum disk space if the disk space is
        # greater than the minimum space required to provision OVSvApp/NCP
        if max_free_space > constants.MIN_PROVISION_SPACE:
            return ds_available_space.get(max_free_space)

    @staticmethod
    def _validate_datastore(datastores, cluster_hosts):
        valid_ds = []
        for ds in datastores:
            if (ds.summary.accessible and
                    ds.summary.maintenanceMode == 'normal'):
                host_mounts = ds.host
                for host_mount in host_mounts:
                    if (host_mount.key in cluster_hosts and
                            host_mount.mountInfo.mounted):
                        valid_ds.append(ds)
        if valid_ds:
            return VMwareUtils._get_max_capacity_datastore(valid_ds)

    @staticmethod
    def _get_cluster_shared_storage(cluster):
        cluster_hosts = cluster.host
        datastores = cluster.datastore
        shared_storages = list()
        for datastore in datastores:
            datastore_hosts = [host.key for host in datastore.host]
            if set(cluster_hosts).issubset(set(datastore_hosts)):
                shared_storages.append(datastore)
        return VMwareUtils._validate_datastore(shared_storages, cluster_hosts)

    @staticmethod
    def _get_single_host_shared_storage(datastores, host_obj):
        ds = dict()
        shared_ds = list()
        models = ["Virtual disk", "LOGICAL VOLUME", "VMware IDE CDR10"]
        for datastore in datastores:
            if datastore.summary.type == 'NFS':
                shared_ds.append(datastore)
                continue
            scsi_disks = datastore.info.vmfs.extent
            ds[datastore] = [scsi_disk.diskName for scsi_disk in
                             scsi_disks]
        luns = host_obj.configManager.storageSystem.storageDeviceInfo.scsiLun
        canonical_names = list()
        for scsi_lun in luns:
            model = (scsi_lun.model).strip()
            if model not in models:
                canonical_names.append(scsi_lun.canonicalName)
        for key, val in ds.iteritems():
            for canonical_name in val:
                if canonical_name in canonical_names:
                    shared_ds.append(key)
        valid_ds = VMwareUtils._validate_datastore(shared_ds, [host_obj])
        if valid_ds:
            return valid_ds
        else:
            LOG.warn("Couldn't find a valid shared datastore for ESXi host "
                     "'{}' Using the local datastore for this host".
                     format(host_obj.name))
            return VMwareUtils.get_local_datastore(host_obj.datastore)

    @staticmethod
    def _is_single_active_host(cluster_hosts, is_new_host):
        count = 0
        for host in cluster_hosts:
            power_state = host.summary.runtime.powerState
            maintenance_mode = host.summary.runtime.inMaintenanceMode
            if is_new_host:
                maintenance_mode = False
            if power_state == 'poweredOn' and not maintenance_mode:
                count += 1
        return True if count == 1 else False

    @staticmethod
    def get_local_datastore(datastores):
        for ds in datastores:
            if ds.summary.type == 'VMFS':
                return ds

    @staticmethod
    def get_shared_datastore(host, is_new_host=False):
        cluster_dict = host['cluster']
        cluster = cluster_dict['obj']
        datastores = host['datastore']
        host_obj = host['obj']
        single_host = VMwareUtils._is_single_active_host(
            cluster_dict['host'], is_new_host)
        if single_host:
            return VMwareUtils._get_single_host_shared_storage(
                datastores, host_obj)
        else:
            return VMwareUtils._get_cluster_shared_storage(cluster)

    @staticmethod
    def _get_virtual_device_spec(device):
        spec = vim.vm.device.VirtualDeviceSpec()
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        spec.device = device
        spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        spec.device.connectable.startConnected = True
        spec.device.connectable.allowGuestControl = True
        return spec

    @staticmethod
    def _get_vnic_spec(pg_obj, nicspec):
        nicspec.device.wakeOnLanEnabled = True
        nicspec.device.deviceInfo = vim.Description()
        if isinstance(pg_obj, vim.dvs.DistributedVirtualPortgroup):
            dvs_port_connection = vim.dvs.PortConnection()
            dvs_port_connection.portgroupKey = pg_obj.key
            dvs_port_connection.switchUuid = \
                pg_obj.config.distributedVirtualSwitch.uuid
            nicspec.device.backing = vim.vm.device. \
                VirtualEthernetCard.DistributedVirtualPortBackingInfo()
            nicspec.device.backing.port = dvs_port_connection
        else:
            nicspec.device.backing = vim.vm.device. \
                VirtualEthernetCard.NetworkBackingInfo()
            nicspec.device.backing.network = pg_obj
            nicspec.device.backing.deviceName = pg_obj.name
        return nicspec

    @staticmethod
    def get_vmxnet3_spec(pg_obj):
        vnicspec = VMwareUtils._get_virtual_device_spec(
            vim.vm.device.VirtualVmxnet3())
        return VMwareUtils._get_vnic_spec(pg_obj, vnicspec)

    @staticmethod
    def get_sriov_spec(pg_obj, fun_id):
        raise NotImplementedError(_("SR-IOV is not implemented"))

        sriovspec = VMwareUtils._get_virtual_device_spec(
            vim.vm.device.VirtualSriovEthernetCard())
        VMwareUtils._get_vnic_spec(pg_obj, sriovspec)
        sriovspec.allowGuestOSMtuChange = True
        sriovspec.device.sriovBacking = (
            vim.vm.device.VirtualSriovEthernetCard.SriovBackingInfo())
        sriovspec.device.sriovBacking. \
            physicalFunctionBacking = (
                vim.vm.device.VirtualPCIPassthrough.DeviceBackingInfo())
        sriovspec.device.sriovBacking.physicalFunctionBacking.id = fun_id

    @staticmethod
    def get_pcipt_spec(host_pci_info, pci_id):
        pci_info = None
        for info in host_pci_info:
            if info.pciDevice.id == pci_id:
                pci_info = info
                break
        if not pci_info:
            raise exception.PCIDeviceNotfoundError(
                _("Couldn't find the PCI device with the provided id '{}'")
                .format(pci_id))
        pcispec = VMwareUtils._get_virtual_device_spec(
            vim.vm.device.VirtualPCIPassthrough())
        pcispec.device.backing = vim.vm.device.VirtualPCIPassthrough. \
            DeviceBackingInfo()
        device_id = hex(pci_info.pciDevice.deviceId % 2**16).lstrip('0x')
        pcispec.device.backing.deviceId = device_id
        pcispec.device.backing.id = pci_info.pciDevice.id
        pcispec.device.backing.systemId = pci_info.systemId
        pcispec.device.backing.vendorId = pci_info.pciDevice.vendorId
        return pcispec

    @staticmethod
    def get_virtual_devices(net_folder, cluster, host, nics):
        devices = []
        sorted_nics = sorted(nics, key=lambda k: k['device'])
        for nic in sorted_nics:
            pg_name = nic['portGroup']
            device_type = nic['type']
            fun_id = nic['pci_id']
            if device_type.lower() == 'vmxnet3':
                pg_obj = net_folder.find_by_name(
                    pg_name, constants.TYPE_PG)
                spec = VMwareUtils.get_vmxnet3_spec(pg_obj)
            elif device_type.lower() == 'sriov':
                spec = VMwareUtils.get_sriov_spec(pg_obj, fun_id)
                VMwareUtils.reserve_memory = True
            elif device_type.lower() == 'pcipt':
                pci_info = cluster.environmentBrowser.QueryConfigTarget(
                    host).pciPassthrough
                if not pci_info:
                    LOG.error("Couldn't find PCI Passthrough Device on "
                              "ESXi host '{}'".format(host.name))
                    return None
                spec = VMwareUtils.get_pcipt_spec(pci_info, fun_id)
            devices.append(spec)
        return devices

    @staticmethod
    def get_vm_config(vm_config, devices, annotation=''):
        vmconf = vim.vm.ConfigSpec(deviceChange=devices)
        if vm_config['cpu']:
            vmconf.numCPUs = int(vm_config['cpu'])
        else:
            LOG.info("Number of CPU has not been provided. "
                     "Installer will use default 4 CPU")
        memory = vm_config['memory_in_mb']
        if memory:
            vmconf.memoryMB = long(memory)
        else:
            LOG.info("Number of RAM has not been provided. "
                     "Installer will use default 4096 MB of RAM")
            memory = 4096
        vmconf.annotation = annotation
        if reserve_guest_memory(vm_config.get('nics')):
            vmconf.memoryReservationLockedToMax = True
            vmconf.memoryAllocation = vim.ResourceAllocationInfo(
                reservation=long(memory))
        return vmconf

    @staticmethod
    def get_relocation_spec(host, resource_pool, datastore):
        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.host = host
        relospec.pool = resource_pool
        return relospec

    @staticmethod
    def clone_vm(si, vm, location, vm_name, vm_folder, vm_config):
        clone_spec = vim.vm.CloneSpec(
            powerOn=True, template=False, location=location, config=vm_config)
        task = vm.Clone(name=vm_name, folder=vm_folder,
                        spec=clone_spec)
        cloned_vm = VMwareUtils.wait_for_task(task, si)
        return cloned_vm

    @staticmethod
    def get_conf_network_details(vm, conf_pg_name):
        conf_ip = None
        conf_mac = None
        nic_infos = vm.guest.net
        if nic_infos:
            for nic in nic_infos:
                if (nic.network and
                        nic.network.lower() == conf_pg_name.lower()):
                    ip_list = nic.ipAddress
                    if ip_list:
                        for ip in ip_list:
                            if is_valid_ipv4(ip):
                                conf_ip = ip
                                conf_mac = nic.macAddress
                                return conf_ip, conf_mac
        return conf_ip, conf_mac

    @staticmethod
    def get_conf_ip_and_mac(vm, conf_pg_name, conf_ip_static):
        retry_count = 0
        while True:
            delay = constants.TASK_WAIT_DELAY
            retry_count += 1
            conf_ip_vc, conf_mac = VMwareUtils.get_conf_network_details(
                vm, conf_pg_name)
            if not conf_ip_static:
                # NCP get_shell_vm_info() which can call this method
                # without static IP. Assign the conf_ip_vc to conf_ip_static.
                conf_ip_static = conf_ip_vc
            if retry_count < constants.NET_INFO_COUNT:
                if all([conf_ip_vc, conf_mac]):
                    # Verify the IP returned by VC is the actual configured
                    # static IP or not.
                    if conf_ip_vc == conf_ip_static:
                        return conf_ip_vc, conf_mac
                LOG.info("Network information not assigned for '{}'. Retrying "
                         "again in {} seconds... {}"
                         .format(vm.name, delay * retry_count, retry_count))
                time.sleep(delay * retry_count)
            else:
                return conf_ip_vc, conf_mac

    @staticmethod
    def _get_command_path(command):
        if command == 'sudo':
            return '/usr/bin/sudo'
        elif command == 'echo':
            return '/bin/echo'
        elif command == 'chmod':
            return '/bin/chmod'

    @staticmethod
    def exec_command_in_guest(content, vm, creds, args, command):
        program_path = VMwareUtils._get_command_path(command)
        cmdspec = vim.vm.guest.ProcessManager.ProgramSpec(
            arguments=args, programPath=program_path)
        content.guestOperationsManager.processManager. \
            StartProgramInGuest(vm=vm, auth=creds, spec=cmdspec)

    @staticmethod
    def send_file_in_guest(content, vm, creds, local_file, target_file):
        url = content.guestOperationsManager.fileManager. \
            InitiateFileTransferToGuest(vm, creds, target_file,
                                        vim.vm.guest.FileManager.
                                        FileAttributes(), len(local_file),
                                        False)
        response = requests.put(url, data=local_file, verify=False)
        return response


class ServiceVMCustomizer:
    def __init__(self, inputs):
        esx_conf_net = inputs.get('esx_conf_net')
        lifecycle_manager = inputs.get('lifecycle_manager')
        self.ssh_key = lifecycle_manager.get('ssh_key')
        self.deploy_node = lifecycle_manager.get('ip_address')
        self.user = lifecycle_manager.get('user')
        self.cidr = esx_conf_net.get('cidr')
        self.gateway = esx_conf_net.get('gateway')

    def _get_slot(self, vm, pci_id):
        extra_configs = vm.config.extraConfig
        query_key = None
        for config in extra_configs:
            if config.value == pci_id:
                query_key = config.key.split('.')[0]
                break
        for config in extra_configs:
            if (config.key.startswith(query_key) and
                    config.key.endswith('pciSlotNumber')):
                return config.value

    def _get_slot2eth_map(self, vm, nics):
        slot_map = list()
        for nic in nics:
            if nic.get('type') == 'pcipt':
                slot = self._get_slot(vm, nic.get('pci_id'))
                slot_map.append("{}:{}".format(nic['device'], slot))
        return ','.join(slot_map)

    def _get_eth2mac_map(self, vm, nics):
        eth2mac = list()
        eths = [nic.get('device') for nic in nics]
        eths.sort()
        devices = vm.config.hardware.device
        for device in devices:
            if isinstance(device.backing, vim.vm.device.VirtualEthernetCard.
                          DistributedVirtualPortBackingInfo):
                eth2mac.append("{}={}".format(eths.pop(0), device.macAddress))
        return ','.join(eth2mac)

    def _send_ssh_key(self, content, vm, creds):
        args = '"{}" > {}'.format(self.ssh_key, constants.GUEST_SSH_KEY)
        VMwareUtils().exec_command_in_guest(content, vm, creds, args, 'echo')
        LOG.info("SSH key file sent successfully to temporary location '{}' "
                 "of '{}'".format(constants.GUEST_SSH_KEY, vm.name))

    def _send_prep_script(self, content, vm, host, creds, params):
        conf_netmask = SharedIPAllocator.get_net_mask(self.cidr)
        conf_vlan = str2list(params['conf_vlan'])
        if len(conf_vlan) < 1:
            conf_vlan = ''
        else:
            conf_vlan = conf_vlan[0]
        if params['conf_vlan_type'] != 'trunk':
            conf_vlan = ''
        script_path = os.path.join(os.path.dirname(
            os.path.abspath(deployer.__file__)), constants.PREP_SCRIPT)
        raw_script = read_file(script_path)
        prep_script = raw_script % (
            params['conf_ip'], conf_vlan,
            conf_netmask, self.gateway, params['device'],
            self.user, self.deploy_node,
            params['pci_slots'], params['eth2mac'],
            params['num_nics'], constants.GUEST_SSH_KEY)
        response = VMwareUtils().send_file_in_guest(
            content, vm, creds, prep_script,
            constants.GUEST_CUSTOMIZATION_SCRIPT)
        status_code = response.status_code
        if not status_code == 200:
            msg = (_("Got '{}' code from the server. Failed to send the "
                   "customization script inside '{}'")
                   .format(status_code, vm.name))
            LOG.exception(msg)
            raise exception.CustomizationError(msg)
        LOG.info("Customization script file '{}' sent successfully inside '{}'"
                 .format(constants.GUEST_CUSTOMIZATION_SCRIPT, vm.name))
        permission_arg = "+x %s" % constants.GUEST_CUSTOMIZATION_SCRIPT
        VMwareUtils().exec_command_in_guest(
            content, vm, creds, permission_arg, 'chmod')

    def customize_service_vm(
            self, content, vm, host, conf_network, conf_ip, nics):
        LOG.info("Waiting for the VM to boot up and the VMWare Tools "
                 "to be ready ...")
        VMwareUtils().wait_for_vmware_tools(vm, host)
        creds = vim.vm.guest.NamePasswordAuthentication(
            username=constants.APPLIANCE_USER,
            password=base64.b64decode(constants.APPLIANCE_PWD))
        params = {}
        params['conf_ip'] = conf_ip
        params['conf_vlan'] = conf_network.get('vlan')
        params['conf_vlan_type'] = conf_network.get('vlan_type')
        params['device'] = conf_network.get('device')
        # TODO: Call this method: self._get_slot2eth_map(vm, nics)
        # When PCIPT will be implemented
        params['pci_slots'] = ''
        params['eth2mac'] = self._get_eth2mac_map(vm, nics)
        params['num_nics'] = len(nics)
        self._send_ssh_key(content, vm, creds)
        self._send_prep_script(content, vm, host, creds, params)
        execute_arg = ("bash {} > customization.log 2>&1"
                       .format(constants.GUEST_CUSTOMIZATION_SCRIPT))
        VMwareUtils().exec_command_in_guest(
            content, vm, creds, execute_arg, 'sudo')


def get_vmconfig_input(inputs, role, net_driver=constants.OVSVAPP_KEY):
    if net_driver == constants.NOOP_NETWORK_DRIVER:
        for config in inputs.get('vm_config'):
            return config if role == constants.PROXY_KEY else None

    __, trunk_pg = get_trunk_dvs_pg(inputs)
    trunk_pg_name = trunk_pg.get('name')
    vm_configs = inputs.get('vm_config')
    for config in vm_configs:
        nics = config.get('nics')
        pgs = [nic['portGroup'] for nic in nics]
        if role == constants.OVSVAPP_KEY and trunk_pg_name in pgs:
                return config
        elif role == constants.PROXY_KEY and trunk_pg_name not in pgs:
                return config


def get_conf_pg(inputs, vm_config):
    portgroups = inputs.get('portGroups')
    nics = vm_config.get('nics')
    conf_pg_name = inputs.get('esx_conf_net').get('portGroup')
    conf_network = None
    for pg in portgroups:
        if pg['name'] == conf_pg_name:
            conf_network = pg
            break
    for nic in nics:
        if nic['portGroup'] == conf_pg_name:
            conf_network['device'] = nic['device']
    return conf_network


def get_trunk_dvs_pg(inputs):
    trunk_dvs = None
    dvswitches = inputs['switches']
    for dvs in dvswitches:
        if not dvs.get('physical_nics'):
            trunk_dvs = dvs
            break
    trunk_pg = None
    portgroups = inputs['portGroups']
    for pg in portgroups:
        if pg['switchName'] == trunk_dvs['name']:
            trunk_pg = pg
            break
    return trunk_dvs, trunk_pg


def reserve_guest_memory(nics):
    for nic in nics:
        if nic.get('type').lower() == 'pcipt':
            return True


def find_by(folder, matcher_method, *args, **kwargs):
    entity_stack = folder.childEntity
    while entity_stack:
        entity = entity_stack.pop()
        if matcher_method(entity, *args, **kwargs):
            yield entity
        elif isinstance(entity, vim.Datacenter):
            entity_stack.append(entity.datastoreFolder)
            entity_stack.append(entity.hostFolder)
            entity_stack.append(entity.networkFolder)
            entity_stack.append(entity.vmFolder)
        elif hasattr(entity, 'childEntity'):
            entity_stack.extend(entity.childEntity)


def find_by_name(folder, name, entity_type=None):
    for entity in find_by(
            folder, lambda item: item.name.lower() == name.lower()):
        if entity_type:
            if isinstance(entity, entity_type):
                return entity
        else:
            return entity


vim.Folder.find_by = find_by
vim.Folder.find_by_name = find_by_name


def is_valid_ipv4(ip):
    return netaddr.valid_ipv4(ip)


def load_json_data(JSON_FILE):
    ip_list = []
    with open(JSON_FILE, 'a+') as json_file:
        json_val = json_file.read()
    if json_val:
        ip_list = json.loads(json_val)
    return ip_list


def update_json_data(json_data, json_file):
    ip_list = load_json_data(json_file)
    ip_list += json_data
    return ip_list


def dump_json_data(json_data, json_file):
    with open(json_file, 'w') as json_content:
        json.dump(json_data, json_content, indent=4, sort_keys=True)


def read_file(input_file):
    with open(input_file, 'rb') as my_file:
        file_content = my_file.read()
    return file_content


def str2bool(flag):
    return flag.lower() in ("yes", "true", "t", "1")


def str2list(input_str):
    if input_str is None:
        return []
    return filter(None, input_str.replace(' ', '').split(','))
