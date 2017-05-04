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
from pyVmomi import vmodl

import eon.common.log as logging
from eon.deployer import constants
from eon.deployer import upload_ova
from eon.deployer import util as deployer_util
from eon.deployer.network.ovsvapp.util import vapp_constants as const
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil

LOG = logging.getLogger(__name__)
vmware_utils = deployer_util.VMwareUtils


class OVSvAppFactory:

    def __init__(self, inputs):
        self.inputs = inputs

    def _error_json(self, **kwargs):
        eon_dict = dict()
        eon_dict['esx_hostname'] = kwargs['name']
        eon_dict['host-moid'] = kwargs['mo_id']
        eon_dict['status_msg'] = kwargs['status_msg']
        eon_dict['status'] = 'failed'
        eon_dict['conf_ip'] = kwargs['conf_ip']
        return eon_dict

    def _get_ovsvapp_name(self, host_name):
        if deployer_util.is_valid_ipv4(host_name):
            ovs_vm_name = "-".join(
                [const.OVS_VAPP_PREFIX, host_name. replace('.', '-')])
        else:
            ovs_vm_name = "-".join([const.OVS_VAPP_PREFIX, host_name])
        return ovs_vm_name

    def _get_ovsvapp_vm_details(self, vm, host, conf_pg_name, role,
                                conf_ip_static):
        eon_dict = dict()
        vm_name = vm.name
        conf_ip, conf_mac = vmware_utils.get_conf_ip_and_mac(
            vm, conf_pg_name, conf_ip_static)
        if not all([conf_ip, conf_mac]):
            err_msg = ("Couldn't retrieve macAddress and ipAddress"
                       " of '{}' . Aborting Installation !".format(vm_name))
            LOG.error(err_msg)
            eon_dict = self._construct_error_json(host, err_msg)
        else:
            msg = ("Successfully created and configured '{}'".format(vm_name))
            LOG.info(msg)
            eon_dict['server_role'] = role
            eon_dict['esx_hostname'] = host['name']
            eon_dict['host-moid'] = host['mo_id']
            eon_dict['ovsvapp_node'] = vm_name
            eon_dict['pxe-mac-addr'] = conf_mac
            eon_dict['pxe-ip-addr'] = conf_ip
            eon_dict['status_msg'] = msg
            eon_dict['status'] = 'success'
        return eon_dict

    def create_vm(self, session, datacenter, host, new_hosts, conf_ip):
        """
        Clone the appliance and create OVSvApp on each host
        """
        try:
            host_name = host['name']
            cluster = host['cluster']
            vm_folder = datacenter['vmFolder']
            net_folder = datacenter['networkFolder']
            creation_error = True
            if not new_hosts:
                resource_pool = cluster['resourcePool']
            else:
                resource_pool = host['obj'].parent.resourcePool

            vm_config = deployer_util.get_vmconfig_input(
                self.inputs, constants.OVSVAPP_KEY)
            devices = vmware_utils.get_virtual_devices(
                net_folder, cluster['obj'], host['obj'], vm_config.get('nics'))
            if devices:
                vmconf = vmware_utils.get_vm_config(
                    vm_config, devices, const.OVS_VAPP_ANNOTATION)
                location = vmware_utils.get_relocation_spec(
                    host['obj'], resource_pool, host['shared_storage'])

                ova_manager = upload_ova.OVAUploadManager(session,
                                        vm_config['template_name'],
                                        vm_config['template_location'],
                                        datacenter, cluster, host,
                                        host['shared_storage'])
                template = ova_manager.upload_ova()

                ovs_vm_name = self._get_ovsvapp_name(host_name)
                LOG.info("Cloning and creating %s ..." % ovs_vm_name)

                cloned_vm = vmware_utils.clone_vm(
                    session['si'], template['obj'], location, ovs_vm_name,
                    vm_folder, vmconf)
                if isinstance(cloned_vm, vim.VirtualMachine):
                    LOG.info("'%s' has been created on host '%s'" %
                             (ovs_vm_name, host_name))
                    if not new_hosts:
                        OVSvAppUtil.disable_ha_on_ovsvapp(
                            session['si'], cloned_vm, cluster, host)

                    conf_network = deployer_util.get_conf_pg(
                        self.inputs, vm_config)
                    customizer = deployer_util.ServiceVMCustomizer(self.inputs)
                    customizer.customize_service_vm(
                        session['content'], cloned_vm, host,
                        conf_network, conf_ip, vm_config.get('nics'))
                    eon_dict = self._get_ovsvapp_vm_details(
                        cloned_vm, host, conf_network.get('name'),
                        vm_config.get('server_role'), conf_ip)
                    creation_error = False
                else:
                    msg = ("Error occurred while cloning %s on "
                           "host %s" % (ovs_vm_name, host_name))
                    LOG.error(msg)
            else:
                msg = ("Either the port group is not part of host "
                       "'%s' Or the port group doesn't exist ! OVSvApp "
                       "won't be deployed on this host"
                       % (host['name']))
                LOG.error(msg)
        except vmodl.MethodFault as e:
            # Vmware related exceptions
            msg = ("Caught VMware API fault: %s" % e.msg)
            LOG.exception(msg)
        except Exception as e:
            # Unknown exceptions
            msg = ("Caught exception: %s" % e)
            LOG.exception(msg)
        finally:
            if creation_error:
                eon_dict = self._error_json(
                            name=host['name'], mo_id=host['mo_id'],
                            status_msg=msg, conf_ip=conf_ip)
        return eon_dict
