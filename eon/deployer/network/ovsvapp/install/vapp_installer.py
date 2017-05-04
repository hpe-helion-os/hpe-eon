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

from eon.common.exception import OVSvAppException
import eon.common.log as logging
from eon.deployer import constants
from eon.deployer import util as deployer_util
from eon.deployer.network.ovsvapp.install.create_ovs_vapp_vm import (
    OVSvAppFactory)
from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil

LOG = logging.getLogger(__name__)


class VappInstaller:

    def __init__(self, inputs):
        self.settings = inputs

    def _create_cluster_vni_tables(self, content, dc_name, cluster):
        vcenter_id = content.about.instanceUuid
        cluster_path = "/".join(
            [dc_name, OVSvAppUtil.get_cluster_inventory_path(
                cluster['obj'], cluster['name'], False)])
        cmd = None
        try:
            neutron = self.settings.get('neutron')
            eon_env = OVSvAppUtil.get_eon_env(neutron)
            cmd = ("neutron ovsvapp-cluster-create --vcenter_id %s "
                   "--clusters %s" % (vcenter_id, cluster_path))
            LOG.info("Executing CLI to create cluster-vni allocations: "
                     "{}".format(cmd))
            command = cmd.split(" ")
            output = OVSvAppUtil.exec_subprocess(command, eon_env)
            if not output:
                raise OVSvAppException(
                    "Got empty response while invoking CLI {}".format(cmd))
        except Exception as e:
            LOG.exception(e)
            raise OVSvAppException(
                "Error occurred while invoking CLI {} : {}".format(cmd, e))

    def _verify_installation(self, si, results, hosts, new_hosts):
        failed_hosts = []
        failed_hosts_ips = []
        for result in results:
            if result.get('status') == 'failed':
                for host in hosts:
                    if host['name'] == result['esx_hostname']:
                        failed_hosts.append(host)
                        failed_hosts_ips.append(result['conf_ip'])
        if failed_hosts:
            if new_hosts:
                [OVSvAppUtil.move_host_back_to_cluster(
                    si, host, host['cluster'], host['folder'], True) for
                    host in failed_hosts]
            else:
                # Note: This will not cause any problem to the cleanup script
                deployer_util.SharedIPAllocator.release_ips(failed_hosts_ips)
                raise OVSvAppException("Failed to import cluster. Results: "
                                       "{}".format(results))

    def _is_old_cluster(self, cluster, trunk_pg_name):
        for pg in cluster.get('network'):
            pg_name = pg.name
            if pg_name in trunk_pg_name and cluster['name'] not in pg_name:
                return True

    def _rename_ovsvapp_trunk_dvspg(self, trunk_dvs, trunk_pg, cluster,
                                    is_new_hosts):
        use_old_trunk_dvs = False
        if (is_new_hosts and
                self._is_old_cluster(cluster, trunk_pg.get('name'))):
            use_old_trunk_dvs = True
        if not use_old_trunk_dvs:
            # Modify all values in the json pointing to trunk dvs and pg
            trunk_dvs_name = trunk_dvs['name']
            trunk_pg_name = trunk_pg['name']
            trunk_dvs['name'] = "-".join([trunk_dvs_name, cluster['name']])
            trunk_pg['switchName'] = trunk_dvs['name']
            nics = deployer_util.get_vmconfig_input(
                self.settings, constants.OVSVAPP_KEY).get('nics')
            trunk_pg['name'] = "-".join([trunk_pg_name, cluster['name']])
            for nic in nics:
                if nic['portGroup'] == trunk_pg_name:
                    nic['portGroup'] = trunk_pg['name']

    def run_installer(self, session, datacenter, cluster, vapp_hosts,
                      is_new_hosts):
        """
        Vapp Installer, which Create the DV Switch first and then
        clone and create the OVSvApp VM
        """
        eon_dict = dict()
        trunk_dvs, trunk_pg = deployer_util.get_trunk_dvs_pg(self.settings)
        self._rename_ovsvapp_trunk_dvspg(
            trunk_dvs, trunk_pg, cluster, is_new_hosts)
        if not is_new_hosts:
            self._create_cluster_vni_tables(
                session['content'], datacenter['name'], cluster)

        network_folder = datacenter['networkFolder']
        vm_folder = datacenter['vmFolder']
        host_folder = datacenter['hostFolder']

        hosts = OVSvAppUtil.get_active_hosts(
            session['content'], vm_folder, vapp_hosts, cluster)

        if is_new_hosts and hosts:
            OVSvAppUtil.create_host_folder(
                session['content'], hosts, host_folder)
            OVSvAppUtil.move_hosts_in_to_folder(session['si'], hosts)

        if hosts:
            try:
                ip_config = self.settings.get('esx_conf_net')
                free_dep_ips = deployer_util.SharedIPAllocator.get_ips(
                    ip_config['cidr'], ip_config['start_ip'],
                    ip_config['end_ip'], ip_config['gateway'],
                    len(hosts))
                network_adapter = NetworkAdapter(session['si'], network_folder)
                network_adapter.configure_dvs_portgroup(self.settings, hosts)
            except Exception as ex:
                if is_new_hosts:
                    [OVSvAppUtil.move_host_back_to_cluster(
                        session['si'], host, host['cluster'], host['folder'],
                        True) for host in hosts]
                raise OVSvAppException(ex)
            exec_args = [(session, datacenter, host, is_new_hosts,
                          deployer_ip) for host, deployer_ip in
                         zip(hosts, free_dep_ips)]
            results = OVSvAppUtil.exec_multiprocessing(
                OVSvAppFactory(self.settings).create_vm, exec_args)
            self._verify_installation(session['si'], results, hosts,
                                      is_new_hosts)

            cluster_path = OVSvAppUtil.get_cluster_inventory_path(
                cluster['obj'], cluster['name'], False)
            cluster_path = "/".join([datacenter['name'], cluster_path])
            trunk_dvs_name = trunk_dvs.get('name')
            cluster_dvs_mapping = ":".join([cluster_path, trunk_dvs_name])
            eon_dict['cluster_dvs_mapping'] = cluster_dvs_mapping
            eon_dict[cluster['name']] = results
        else:
            msg = "Couldn't find any valid host to continue installation"
            LOG.error(msg)
        return eon_dict
