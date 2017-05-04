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

import contextlib

from mock import patch

from eon.common.exception import OVSvAppException
from eon.deployer import util
from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.deployer.network.ovsvapp.install.vapp_installer import VappInstaller
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


class Network:
    name = 'TRUNK'


class Content:

    class about:
        instanceUuid = '94485AFF-C576-4625-B255-09FC7C9B55E8'


class TestVappInstaller(tests.BaseTestCase):

    def setUp(self):
        super(TestVappInstaller, self).setUp()
        self.vapp_installer = VappInstaller(fake_inputs.data)

    def test_create_cluster_vni_tables(self):
        with contextlib.nested(
            patch.object(OVSvAppUtil, 'get_cluster_inventory_path',
                         return_value='DC/Cluster1'),
            patch.object(OVSvAppUtil, 'get_eon_env'),
            patch.object(OVSvAppUtil, 'exec_subprocess')) as (
                mock_get_cluster_inventory_path, mock_get_eon_env,
                mock_exec_subprocess):
            self.vapp_installer._create_cluster_vni_tables(
                Content, 'dc_name', fake_inputs.fake_clusters)
            self.assertTrue(mock_get_cluster_inventory_path.called)
            self.assertTrue(mock_get_eon_env.called)
            self.assertTrue(mock_exec_subprocess.called)

    def test_verify_installation(self):
        results = [{'status': 'failed', 'esx_hostname': 'ESX-1',
                    'conf_ip': '10.10.10.10'}]
        hosts = [{'name': 'ESX-1',
                  'cluster': 'fake-cluster',
                  'folder': 'fake-folder'}]
        with patch.object(OVSvAppUtil, 'move_host_back_to_cluster') as (
                mock_move_host_back_to_cluster):
            self.vapp_installer._verify_installation(fake_inputs.session,
                                                     results, hosts,
                                                     'new_hosts')
            self.assertTrue(mock_move_host_back_to_cluster.called)

    def test_verify_installation_release_ip(self):
        results = [{'status': 'failed', 'esx_hostname': 'ESX-1',
                    'conf_ip': '10.10.10.10'}]
        hosts = [{'name': 'ESX-1',
                  'cluster': 'fake-cluster',
                  'folder': 'fake-folder'}]
        with contextlib.nested(
                patch.object(OVSvAppUtil, 'move_host_back_to_cluster'),
                patch.object(util.SharedIPAllocator, 'release_ips')) as (
                mock_move_host_back_to_cluster, mock_release_ips):
                self.assertRaises(
                    OVSvAppException,
                    lambda: self.vapp_installer._verify_installation(
                        fake_inputs.session, results, hosts, None))
                self.assertFalse(mock_move_host_back_to_cluster.called)
                self.assertTrue(mock_release_ips.called)

    def test_is_old_cluster(self):
        trunk_pg = 'TRUNK_CLuster1'
        cluster = {'network': [Network], 'name': 'Cluster1'}
        output = self.vapp_installer._is_old_cluster(cluster, trunk_pg)
        self.assertTrue(output)

    def test_invalid_is_old_cluster_(self):
        trunk_pg = 'TRUNK_CLuster1'
        n = Network()
        n.name = 'TRUNK-Cluster1'
        cluster = {'network': [n], 'name': 'Cluster1'}
        output = self.vapp_installer._is_old_cluster(cluster, trunk_pg)
        self.assertFalse(output)

    def test_rename_ovsvapp_trunk_dvspg_fresh_activation(self):
        cluster = fake_inputs.fake_clusters
        trunk_dvs = {'name': 'TRUNK-DVS'}
        trunk_pg = {'name': 'TRUNK-PG'}
        renamed_trunk_dvs_name = "-".join([trunk_dvs.get('name'),
                                           cluster.get('name')])
        renamed_trunk_pg_name = "-".join([trunk_pg.get('name'),
                                          cluster.get('name')])
        with patch.object(self.vapp_installer, '_is_old_cluster',
                          return_value=False) as mock_is_old_cluster:
            self.vapp_installer._rename_ovsvapp_trunk_dvspg(
                trunk_dvs, trunk_pg, cluster, False)
            self.assertFalse(mock_is_old_cluster.called)
            self.assertEqual(renamed_trunk_dvs_name, trunk_dvs['name'])
            self.assertEqual(renamed_trunk_pg_name, trunk_pg['name'])

    def test_rename_ovsvapp_trunk_dvspg_old_commissioning(self):
        cluster = fake_inputs.fake_clusters
        trunk_dvs = {'name': 'TRUNK-DVS'}
        trunk_pg = {'name': 'TRUNK-PG'}
        with patch.object(self.vapp_installer, '_is_old_cluster',
                          return_value=True) as mock_is_old_cluster:
            self.vapp_installer._rename_ovsvapp_trunk_dvspg(
                trunk_dvs, trunk_pg, cluster, True)
            self.assertTrue(mock_is_old_cluster.called)
            self.assertEqual(trunk_dvs['name'], trunk_dvs['name'])
            self.assertEqual(trunk_pg['name'], trunk_pg['name'])

    def test_rename_ovsvapp_trunk_dvspg_new_commissioning(self):
        cluster = fake_inputs.fake_clusters
        trunk_dvs = {'name': 'TRUNK-DVS'}
        trunk_pg = {'name': 'TRUNK-PG'}
        renamed_trunk_dvs_name = "-".join([trunk_dvs.get('name'),
                                           cluster.get('name')])
        renamed_trunk_pg_name = "-".join([trunk_pg.get('name'),
                                          cluster.get('name')])
        with patch.object(self.vapp_installer, '_is_old_cluster',
                          return_value=False) as mock_is_old_cluster:
            self.vapp_installer._rename_ovsvapp_trunk_dvspg(
                trunk_dvs, trunk_pg, cluster, True)
            self.assertTrue(mock_is_old_cluster.called)
            self.assertEqual(renamed_trunk_dvs_name, trunk_dvs['name'])
            self.assertEqual(renamed_trunk_pg_name, trunk_pg['name'])

    def test_run_installer(self):
        self.vapp_installer.settings['network_type'] = 'vxlan'
        fake_inputs.fake_datacenter['name'] = 'fake_DC'
        with contextlib.nested(
            patch.object(util, 'get_trunk_dvs_pg',
                         return_value=[{'name': 't1'}, 't2']),
            patch.object(VappInstaller, '_rename_ovsvapp_trunk_dvspg'),
            patch.object(OVSvAppUtil, 'get_active_hosts'),
            patch.object(OVSvAppUtil, 'create_host_folder'),
            patch.object(OVSvAppUtil, 'move_hosts_in_to_folder'),
            patch.object(util.SharedIPAllocator, 'get_ips',
                         return_value=['10.10.10.2', '10.10.10.3']),
            patch.object(NetworkAdapter, 'configure_dvs_portgroup'),
            patch.object(OVSvAppUtil, 'exec_multiprocessing'),
            patch.object(VappInstaller, '_verify_installation'),
            patch.object(OVSvAppUtil, 'get_cluster_inventory_path',
                         return_value='DC1/Cluster')) as (
                mock_get_trunk_dvs_pg, mock_rename_ovsvapp_trunk_dvspg,
                mock_get_active_hosts, mock_create_host_folder,
                mock_move_hosts_in_to_folder, mock_get_ips,
                mock_configure_dvs_portgroup,
                mock_exec_multiprocessing, mock_verify_installation,
                mock_get_cluster_inventory_path):
            output = self.vapp_installer.run_installer(
                fake_inputs.session, fake_inputs.fake_datacenter,
                fake_inputs.fake_clusters, 'vapp_hosts',
                'is_new_hosts')
            self.assertEqual('fake_DC/DC1/Cluster:t1',
                             output['cluster_dvs_mapping'])
            self.assertTrue('Cluster1' in output)
            self.assertTrue(mock_get_trunk_dvs_pg.called)
            self.assertTrue(mock_rename_ovsvapp_trunk_dvspg.called)
            self.assertTrue(mock_get_active_hosts.called)
            self.assertTrue(mock_create_host_folder.called)
            self.assertTrue(mock_move_hosts_in_to_folder.called)
            self.assertTrue(mock_get_ips.called)
            self.assertTrue(mock_configure_dvs_portgroup.called)
            self.assertTrue(mock_exec_multiprocessing.called)
            self.assertTrue(mock_verify_installation.called)
            self.assertTrue(mock_get_cluster_inventory_path.called)
