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
import eon.common.log as logging
from eon.deployer import constants
from eon.deployer.network.ovsvapp.util import vapp_constants
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.deployer.util import VMwareUtils

LOG = logging.getLogger(__name__)


def move_host_back_to_cluster(inputs):
    host_name = inputs.get('host_name')
    err = inputs.get('status') == constants.HOST_COMM_FAILURE
    si = VMwareUtils.get_vcenter_session(
        inputs['vcenter_host'], inputs['vcenter_https_port'],
        inputs['vcenter_username'], inputs['vcenter_password'])

    host_view = VMwareUtils.get_view_ref(
        si.content, si.content.rootFolder, [vim.HostSystem])
    host_prop = ['name', 'vm']
    host_refs = VMwareUtils.collect_properties(
        si.content, host_view, vim.HostSystem, host_prop, True)
    host = None
    for host_ref in host_refs:
        if host_ref['name'] == host_name:
            host = host_ref
            break
    if not host:
        raise OVSvAppException("Couldn't find the commissioned host '{}'"
                               .format(host_name))
    datacenter = OVSvAppUtil.get_host_parent(host['obj'], vim.Datacenter)
    prep_folder = OVSvAppUtil.get_host_parent(host['obj'], vim.Folder)
    if prep_folder.name != 'host':
        cluster_id = prep_folder.name
        cluster = VMwareUtils.get_cluster(
            si.content, datacenter.hostFolder, cluster_id)
        if not cluster:
            raise OVSvAppException(_("Couldn't find the Cluster from the prep "
                                   "folder name !"))
        OVSvAppUtil.move_host_back_to_cluster(
            si, host, cluster, prep_folder, err)
        if not err:
            vm_obj = get_ovsvapp_from_host(host)
            OVSvAppUtil.disable_ha_on_ovsvapp(si, vm_obj, cluster, host)


def get_ovsvapp_from_host(host):
    for vm in host['vm']:
        if vapp_constants.OVS_VAPP_IDENTIFIER in vm.config.annotation:
            return vm
