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

from eon.tests.unit import utils


class DbTestcaseV2(utils.DbTestCase):

    def _assert_rsc_mgr(self, mgr1, mgr2):
        self.assertEqual(mgr1['name'], mgr2['name'])
        self.assertEqual(mgr1['ip_address'], mgr2['ip_address'])
        self.assertEqual(mgr1['username'], mgr2['username'])
        self.assertEqual(mgr1['password'], mgr2['password'])
        self.assertEqual(mgr1['port'], mgr2['port'])
        self.assertEqual(mgr1['type'], mgr2['type'])

    def _assert_is_not_deleted(self, obj):
        self.assertNotEqual(obj.get('id'), None)
        self.assertEqual(obj.get('deleted_at'), None)

    def _assert_is_deleted(self, obj):
        self.assertNotEqual(obj.get('id'), None)
        self.assertIsNotNone(obj.get('deleted_at'))

    def _assert_rsc_esx_cluster(self, rsc1, rsc2):
        self.assertEqual(rsc1['name'], rsc2['name'])
        self.assertEqual(rsc1['type'], rsc2['type'])
        self.assertEqual(rsc1['state'], rsc2['state'])
        self.assertEqual(rsc1['resource_mgr_id'], rsc2['resource_mgr_id'])

    def _assert_rsc_kvm(self, rsc1, rsc2):
        self.assertEqual(rsc1['name'], rsc2['name'])
        self.assertEqual(rsc1['type'], rsc2['type'])
        self.assertEqual(rsc1['state'], rsc2['state'])
        self.assertEqual(rsc1['ip_address'], rsc2['ip_address'])
        self.assertEqual(rsc1['username'], rsc2['username'])
        self.assertEqual(rsc1['password'], rsc2['password'])
        self.assertEqual(rsc1.get('resource_mgr_id'),
                         rsc2.get('resource_mgr_id'))
        self.assertIsNone(rsc1.get('resource_mgr_id'))
        self.assertIsNone(rsc2.get('resource_mgr_id'))

    def _assert_property(self, key, val, parent_id, prop):
        self.assertEqual(key, prop['key'])
        self.assertEqual(val, prop['value'])
        self.assertEqual(parent_id, prop['parent_id'])
