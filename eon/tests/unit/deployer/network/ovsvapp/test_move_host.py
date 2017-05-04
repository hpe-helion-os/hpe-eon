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

from pyVmomi import vim

from eon.deployer.network.ovsvapp.install import move_host
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.deployer.util import VMwareUtils
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


vc_info = fake_inputs.data.get('vcenter_configuration')
cluster_id = vc_info.get('cluster')


class VM:

    class config:
        annotation = ['hp-ovsvapp']


class PrepFolder:
    name = cluster_id


class Host:
    parent = 'fake-parent'


class TestMoveHost(tests.BaseTestCase):

    def setUp(self):
        super(TestMoveHost, self).setUp()

    def test_commissioned_folder_name(self):
        with patch.object(OVSvAppUtil, 'get_host_parent',
                          return_value=PrepFolder):
            folder = OVSvAppUtil.get_host_parent(Host, vim.Folder)
            self.assertEqual(folder.name, cluster_id)

    def test_move_host_back_to_cluster(self):
        host = [{'name': 'fake-host', 'obj': 'host-obj'}]
        fake_inputs.data['host_name'] = 'fake-host'
        fake_inputs.data['vcenter_host'] = '10.10.10.10'
        fake_inputs.data['vcenter_https_port'] = 443
        fake_inputs.data['vcenter_username'] = 'user'
        fake_inputs.data['vcenter_password'] = 'password'
        with contextlib.nested(
            patch.object(VMwareUtils, 'get_vcenter_session',
                         return_value=fake_inputs.MOB),
            patch.object(VMwareUtils, 'get_view_ref'),
            patch.object(VMwareUtils, 'collect_properties',
                         return_value=host),
            patch.object(OVSvAppUtil, 'get_host_parent',
                         retunr_value=PrepFolder()),
            patch.object(VMwareUtils, 'get_cluster'),
            patch.object(move_host, 'get_ovsvapp_from_host'),
            patch.object(OVSvAppUtil, 'disable_ha_on_ovsvapp'),
            patch.object(OVSvAppUtil, 'move_host_back_to_cluster')) as (
                mock_get_vcenter_session, mock_get_view_ref,
                mock_collect_properties, mock_get_host_parent,
                mock_get_cluster, mock_get_ovsvapp_from_host,
                mock_disable_ha_on_ovsvapp,
                mock_move_host_back_to_cluster):
            move_host.move_host_back_to_cluster(fake_inputs.data)
            self.assertTrue(mock_get_vcenter_session.called)
            self.assertTrue(mock_get_view_ref.called)
            self.assertTrue(mock_collect_properties.called)
            self.assertTrue(mock_get_host_parent.called)
            self.assertTrue(mock_get_cluster.called)
            self.assertTrue(mock_get_ovsvapp_from_host.called)
            self.assertTrue(mock_disable_ha_on_ovsvapp.called)
            self.assertTrue(mock_move_host_back_to_cluster.called)

    def test_get_ovsvapp_from_host(self):
        host = {'vm': [VM]}
        output = move_host.get_ovsvapp_from_host(host)
        self.assertEqual(['hp-ovsvapp'], output.config.annotation)
