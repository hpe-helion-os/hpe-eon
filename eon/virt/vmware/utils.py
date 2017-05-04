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
from eon.common import exception
from eon.openstack.common import log
from oslo_config import cfg
from eon.virt.vmware.constants import HLINUX_OVA_TEMPLATE_NAME
from eon.virt.vmware.constants import UPLOAD_TO_CLUSTER

CONF = cfg.CONF

LOG = log.getLogger(__name__)


def frame_network_data(vc_data, network_prop, dc_name):
    network_data = {"vcenter_configuration": vc_data}
    # Cluster entry not required to trigger setup/teardown network
    network_data["vcenter_configuration"]["cluster"] = None
    network_data["vcenter_configuration"]["datacenter"] = dc_name
    network_data.update(network_prop)
    return network_data


def frame_provision_data(vc_data, cluster_data, network_prop):
    cluster_inventory = cluster_data['inventory']
    provision_data = {"vcenter_configuration": vc_data}
    provision_data["vcenter_configuration"]["cluster"] = cluster_data['name']
    provision_data["vcenter_configuration"]["cluster_moid"] = (
        get_cluster_property(cluster_data, "cluster_moid"))
    provision_data["vcenter_configuration"]["datacenter"] = (
        cluster_inventory['datacenter']['name'])

    update_lifecycle_manager_info(network_prop)
    update_ova_template_info(cluster_data, network_prop)
    provision_data.update(network_prop)
    return provision_data


def update_lifecycle_manager_info(net_prop):
    """
    Update network_prop with the lifecycle_manager info from conductor conf
    "lifecycle_manager":  {
        "hlm_version": "4.0.0",
        "ip_address": "10.20.16.2",
        "ssh_key": "ssh-rsa AAAAAB3NzacCy stack@company.org",
        "user": "stack"
        }
    """
    lcm_version = CONF.lifecycle_manager.hlm_version
    net_prop["lifecycle_manager"] = {
        "ip_address": CONF.lifecycle_manager.ip_address,
        "ssh_key": CONF.lifecycle_manager.ssh_key,
        "user": CONF.lifecycle_manager.user,
        "hlm_version": lcm_version.split('-')[-1]
    }


def update_ova_template_info(cluster_data, network_prop):
    """
    Update network_prop with the ova template name and location.
    "vm_config": [
       {
        "server_role": "ESX-COMPUTE-ROLE",
        "template_name": "hlm-shell-vm",
        "template_location": "//local"
        },
       {
        "server_role": "OVSVAPP-ROLE",
        "template_name": "hlm-shell-vm",
        "template_location": "//local"
        }
        ]
    """
    hlm_version = network_prop.get("lifecycle_manager").get("hlm_version")
    template_info = network_prop.get("template_info", {})

    is_upload_to_cluster = template_info.get(UPLOAD_TO_CLUSTER)
    if is_upload_to_cluster:
        template_name = (HLINUX_OVA_TEMPLATE_NAME + "-" + hlm_version +
                         "-" + cluster_data['name'])
    else:
        dc_name = cluster_data["inventory"]['datacenter']['name']
        template_name = (HLINUX_OVA_TEMPLATE_NAME + "-" + hlm_version +
                         "-" + str(dc_name))

    template_location = (CONF.vmware.template_location or
                         template_info.get("template_location", ""))
    for vm_config in network_prop.get("vm_config"):
        vm_config["template_name"] = template_name
        vm_config["template_location"] = template_location


def get_cluster_property(cluster_data, property_name):
    cluster_meta_data = cluster_data['meta_data']
    for data in cluster_meta_data:
        if data['name'] == property_name:
            return data['value']


def process_ovsvapp_network_info(network_info):
    """
    :param network_info [{'status': 'failed', 'host-moid': u'host-459',
                        'status_msg': 'Error',
                        'esx_hostname': '10.1.221.78'},
                        ]
    """
    host_data_info = []
    for info in network_info:
        if info.get("status") == "failed":
            # if only one host is there, raise the exception
            msg = (_("Host commission failed for %s. Error: %s ") %
                   (info.get("esx_hostname"), info.get('status_msg')))
            if len(network_info) == 1:
                raise exception.OVSvAppException(msg)
            else:
                LOG.warn(msg)
                continue

        host_data_info.append(info)

    return host_data_info


def strip_current_ovsvapp_host_info(current_list, db_list):
    """
    current_list items needs to be removed from the db_list
    if any item matches.
    Assumes, db_list will always be larger than current_list
    :param db_list [{'name': 1}, {'name' : 2}]
    :param current_list [{'name': 1}]
    :return [{'name' : 2}]
    """
    li = []
    if len(current_list) < len(db_list):
        for j in db_list:
            found = 0
            for i in current_list:
                if j["esx_hostname"] == i["esx_hostname"]:
                    found = 1
                    break

            if not found:
                li.append(j)

        return li
    else:
        return db_list


def validate_vcenter_version(vc_version, vc_build):
    """
    This will compare the vCenter version and build numbers with
    the configured support matrix values.
    @param vc_version: verison number fetched from vCenter
    @param vc_build : build number fetched from vCenter
    """
    vc_supported_version = CONF.vc_supported_version
    LOG.info("vCenter support Matrix: %s" % vc_supported_version)

    version_list = [item.split(':')[0] for item in vc_supported_version]
    if vc_version < min(version_list):
        return False

    for item in vc_supported_version:
        items = item.split(':')
        if (items[0] == vc_version) and (int(vc_build) < int(items[1])):
            LOG.error("Supported build number (%s) is greater than the "
                        "actual build number (%s) for the vCenter "
                        "version (%s)" % (
                            items[1], vc_build, vc_version))
            return False

    return True
