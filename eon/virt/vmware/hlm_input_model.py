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

from eon.common import utils
from eon.common.constants import BaseConstants as base_const
from eon.common.constants import HLMCConstants as hlm_const
from eon.common.constants import ResourceConstants as res_const
from eon.virt import constants as virt_const
from eon.virt.vmware import constants


def _build_server_id(cluster_data, unique_id):
    vcenter_info = cluster_data[res_const.RESOURCE_MANAGER_INFO]
    return utils.get_hash(vcenter_info[base_const.RESOURCE_MGR_ID] + unique_id)


def _build_compute_proxy_info(proxy_node_info, action, cluster_data,
                              input_model_data):
    # update compute proxy info
    if not proxy_node_info:
        return []

    server_id = _build_server_id(cluster_data,
                                 proxy_node_info[constants.CLUSTER_MOID])
    server_role_name = (proxy_node_info.get('server_role')
                        if proxy_node_info.get('server_role')
                            else constants.DEFAULT_COMPUTE_PROXY_ROLE_NAME)
    proxy_info = {hlm_const.SERVER_ID: server_id,
                  hlm_const.SERVER_IPADDR: str(proxy_node_info['pxe-ip-addr']),
                  hlm_const.SERVER_ROLE: server_role_name}
    if action == virt_const.INPUT_MODEL_ADD:
        if input_model_data and input_model_data.get('server_group'):
            proxy_info[hlm_const.SERVER_GROUP] = (
                                    input_model_data['server_group'])
    return proxy_info


def _build_network_driver_info(ovsvapp_node_info, action, cluster_data,
                               input_model_data):
    # update network_driver info
    nw_node_info = []
    if not ovsvapp_node_info:
        return nw_node_info

    for node in ovsvapp_node_info:
        server_id = _build_server_id(cluster_data, node['host-moid'])
        server_role_name = (node.get('server_role') if node.get('server_role')
                            else constants.DEFAULT_NETWORK_DRIVER_ROLE_NAME)
        ovsvapp_info = {hlm_const.SERVER_ID: server_id,
                        hlm_const.SERVER_IPADDR: str(node.get('pxe-ip-addr')),
                        hlm_const.SERVER_ROLE: server_role_name}
        if action == virt_const.INPUT_MODEL_ADD:
            if input_model_data and input_model_data.get('server_group'):
                ovsvapp_info[hlm_const.SERVER_GROUP] = (
                                            input_model_data['server_group'])
        nw_node_info.append(ovsvapp_info)

    return nw_node_info


def _build_passthrough_info(cluster_data):
    vcenter_info = cluster_data[res_const.RESOURCE_MANAGER_INFO]
    passthrough_info = {
                  "vmware": {
                    "vcenter_cluster": cluster_data[base_const.NAME_KEY],
                    "vcenter_id": vcenter_info[base_const.RESOURCE_MGR_ID]
                    }
                }
    return passthrough_info


def _build_proxy_passthrough_info(proxy_node_info, cluster_data):
    if not proxy_node_info:
        return []

    server_id = _build_server_id(cluster_data,
                                 proxy_node_info[constants.CLUSTER_MOID])
    passthrough_info = _build_passthrough_info(cluster_data)
    proxy_passthrough_info = {'id': server_id,
                              'data': passthrough_info}
    return proxy_passthrough_info


def _build_ovsvapp_passthrough_info(ovsvapp_info, cluster_data,
                                    cluster_dvs_mapping):
    """
    :param network_proxy_info : [{"status": "success", "host-moid": "host-506",
        "esx_hostname": "10.1.221.76", "server_role": "OVSVAPP-ROLE",
        "pxe-ip-addr": "192.168.10.103"}]
    """
    nw_proxy_passthrough_info = []
    if not ovsvapp_info:
        return []

    for node in ovsvapp_info:
        server_id = _build_server_id(cluster_data, node['host-moid'])
        passthrough_info = _build_passthrough_info(cluster_data)
        passthrough_info['vmware'].update({
                    "cluster_dvs_mapping": cluster_dvs_mapping,
                    "esx_hostname": str(node[constants.ESX_HOST_NAME])
                    })
        nw_proxy_passthrough_info.append({'id': server_id,
                                          'data': passthrough_info})
    return nw_proxy_passthrough_info


def build_servers_info(hlm_prop, action, cluster_data,
                       input_model_data):
    '''
    returns:

    { id: esx-compute-001
      ip-addr: "192.168.10.10"
      role: "ESX-COMPUTE-ROLE"
    }
    '''
    cluster_name = cluster_data[base_const.NAME_KEY]
    cluster_details = hlm_prop.get(constants.NETWORK_DRIVER).get(cluster_name)

    proxy_info = _build_compute_proxy_info(
                        hlm_prop.get(constants.ESX_PROXY_NAME),
                        action,
                        cluster_data,
                        input_model_data)
    nw_node_info = []
    if cluster_details:
        nw_node_info = _build_network_driver_info(
                            cluster_details,
                            action,
                            cluster_data,
                            input_model_data)
    return proxy_info, nw_node_info


def build_passthrough_info(hlm_prop, cluster_data):
    '''
    :returns
    { id: esx-compute1
      data {
        vmware:
          vcenter_cluster: cluster1
          vcenter_id: 2e5043fc-ae08-4707-a00b-59e383b245b6
          }
    }
    '''
    cluster_name = cluster_data[base_const.NAME_KEY]
    net_driver = hlm_prop.get(constants.NETWORK_DRIVER)
    cluster_details = net_driver.get(cluster_name)

    proxy_info = _build_proxy_passthrough_info(
                    hlm_prop.get(constants.ESX_PROXY_NAME),
                    cluster_data)

    ovsvapp_info = []
    if cluster_details:
        cluster_dvs_mapping = net_driver.get(constants.CLUSTER_DVS_MAPPING)
        ovsvapp_info = _build_ovsvapp_passthrough_info(
                                cluster_details,
                                cluster_data,
                                cluster_dvs_mapping)
    return proxy_info, ovsvapp_info
