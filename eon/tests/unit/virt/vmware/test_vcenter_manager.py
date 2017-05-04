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
import eventlet
import mock

from eon.virt.vmware import inventory_collector
from eon.virt.vmware import vcenter_manager
from testtools import TestCase
from eon.virt.vmware import utils


class TestVcenterManager(TestCase):

    def setUp(self):
        super(TestVcenterManager, self).setUp()
        self.vcdata = {"ip_address": "192.168.1.3",
                       'username': 'user',
                       'password': 'password'}
        self.vcm = vcenter_manager.vCenterManager()

    def test_add_vcenter(self):
        vcenter_version = "4.1:699731"
        session_mock = mock.MagicMock()
        inv_mock = mock.MagicMock()
        with contextlib.nested(
            mock.patch.object(self.vcm, "_get_vcenter_version"),
            mock.patch.object(inventory_collector, "VCInventoryCollector"),
            mock.patch.object(self.vcm, "_get_vcenter_uuid"),
            mock.patch.object(utils, "validate_vcenter_version")
                ) as (about_con, _inv_coll, get_vuuid,
                      val_version):
            about_con.return_value = ("10.10", "10.10.1", session_mock)
            _inv_coll.return_value = inv_mock
            val_version.return_value = vcenter_version
            get_vuuid.return_value = "1234"
            vc_data = self.vcm.add_vcenter(self.vcdata)
            self.assertEqual(vc_data['id'], '1234')

    def test_get_vcenter_info(self):
        session_mock = mock.MagicMock()
        with mock.patch.object(vcenter_manager, "VMwareAPISession") \
                as session_m:
            session_m.return_value = session_mock
            self.assertTrue(self.vcm.get_vcenter_info(self.vcdata))

    def test_get_registered_clusters(self):
        db_vc_resources = [{"name": "cluster1", "type": "esxcluster",
                            "id": "1234"}]
        db_vc_resources_prop = {"1234": [{"id": "456", "key": "cluster_moid",
                                          "value": "domain-20"}]}
        cluster_list = self.vcm._get_registered_clusters(db_vc_resources,
                                          db_vc_resources_prop)
        self.assertEquals(cluster_list[0], ("domain-20", "cluster1"))

    def test_get_clusters_not_imported_state(self):
        db_vc_resources = [{"name": "cluster1", "type": "esxcluster",
                            "id": "1234", "state": "activated"}]
        db_vc_resources_prop = {"1234": [{"id": "456", "key": "cluster_moid",
                                          "value": "domain-20"}]}
        cluster_list = self.vcm._get_clusters_not_imported_state(
            db_vc_resources, db_vc_resources_prop)
        self.assertEquals(cluster_list[0], "domain-20")

    def test_poll_vcenter_resources(self):
        cluster_names = [('domain-c1997', 'esx-app-cluster'),
                         ('domain-c1998', 'esx-app-cluster1'),
                         ('domain-c2000', 'esx-app-cluster3')]
        db_clus_names = [('domain-c1997', 'esx-app-cluster'),
                         ('domain-c1999', 'esx-app-cluster2')]
        act_clus_names = ['domain-c2000']
        new_exp = [('domain-c1998', 'esx-app-cluster1')]
        rem_exp = [('domain-c1999', 'esx-app-cluster2')]
        inv_mock = mock.MagicMock()
        with mock.patch.object(self.vcm, "get_vcenter_inventory_collector") \
                as get_inv_coll:
            get_inv_coll.return_value = inv_mock
            with contextlib.nested(
                mock.patch.object(inv_mock, "get_cluster_names"),
                mock.patch.object(self.vcm, "_get_registered_clusters"),
                mock.patch.object(self.vcm,
                                  "_get_clusters_not_imported_state")) \
                    as (get_clus_names, get_reg_clus, get_act_clus):
                get_clus_names.return_value = cluster_names
                get_reg_clus.return_value = db_clus_names
                get_act_clus.return_value = act_clus_names
                (new, rem) = self.vcm.poll_vcenter_resources(self.vcdata,
                                                "db_vc_resources",
                                                "db_vc_resources_prop")
                self.assertEquals(new, new_exp)
                self.assertEquals(rem, rem_exp)

    def test_monitor_events(self):
        with mock.patch.object(eventlet, "spawn_n"):
            self.assertIsNone(self.vcm.monitor_events(self.vcdata))

    def test_update_vc_cache(self):
        with mock.patch.object(self.vcm, "add_vcenter"):
            self.assertIsNone(self.vcm.update_vc_cache(self.vcdata))

    def test_delete_vcenter(self):
        inv_mock = mock.MagicMock()
        self.vcm.registered_vcenters = {"192.168.1.3": inv_mock}
        self.assertIsNone(self.vcm.delete_vcenter(self.vcdata))
        self.assertEquals(self.vcm.registered_vcenters, {})
