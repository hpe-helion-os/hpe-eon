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
import mock

from testtools import TestCase
from eon.conductor.v2 import manager


class TestConductorManager(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        manager.manager = mock.MagicMock()
        manager.greenpool = mock.MagicMock()
        self.context = "context"
        self.manager = manager.ConductorManager("host", "topic")

    def test_get_all_resource_mgrs(self):
        expected = {'1234': {'id': '1234', "type": 'vcenter'},
                    '5678': {'id': "5678", "type": 'vcenter'}}
        with mock.patch.object(self.manager._resource_mgr, "get_all") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter'},
                                         '5678': {'id': "5678",
                                                  "type": 'vcenter'}}
            self.assertEqual(expected,
                             self.manager.get_all_resource_mgrs(self.context))

    def test_get_all_resource_mgrs_empty(self):
        with mock.patch.object(self.manager._resource_mgr, "get_all") \
                        as get_all_mock:
            get_all_mock.return_value = []
            self.assertEqual([],
                             self.manager.get_all_resource_mgrs(self.context))

    def test_get_resource_mgr(self):
        expected = {'1234': {'id': '1234', "type": 'vcenter'}}
        with mock.patch.object(self.manager._resource_mgr, "get") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter'}}
            self.assertEqual(expected,
                             self.manager.get_resource_mgr(self.context,
                                                           '1234', False))

    def test_get_resource_mgr_with_inventory(self):
        expected = {'1234': {'id': '1234', "type": 'vcenter'}}
        with mock.patch.object(self.manager._resource_mgr,
                               "get_with_inventory") as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter'}}
            self.assertEqual(expected,
                             self.manager.get_resource_mgr(self.context,
                                                           '1234', True))

    def test_create_resource_mgr(self):
        expected = {'1234': {'id': '1234', "type": 'vcenter'}}
        with mock.patch.object(self.manager._resource_mgr, "create") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter'}}
            self.assertEqual(expected,
                            self.manager.create_resource_mgr(self.context,
                            'create_data'))

    def test_update_resource_mgr(self):
        expected = {'1234': {'id': '1234', "type": 'vcenter'}}
        with mock.patch.object(self.manager._resource_mgr, "update") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter'}}
            self.assertEqual(expected,
                            self.manager.update_resource_mgr(self.context,
                            "1234", 'updata_data'))

    def test_delete_resource_mgr(self):
        with mock.patch.object(self.manager._resource_mgr, "delete") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter'}}
            self.assertTrue(self.manager.delete_resource_mgr(self.context,
                            '1234'))

    def test_get_all_resources(self):
        expected = [{'1234': {'id': '1234', "type": 'esxcluster'},
                    '5678': {'id': "5678", "type": 'hyperv'}}]
        with mock.patch.object(self.manager._resource, "get_all") \
                        as get_all_mock:
            get_all_mock.return_value = [{'1234': {'id': '1234',
                                                  "type": 'esxcluster'},
                                         '5678': {'id': "5678",
                                                  "type": 'hyperv'}}]
            self.assertEqual(expected,
                             self.manager.get_all_resources(self.context))

    def test_get_all_resources_empty(self):
        with mock.patch.object(self.manager._resource, "get_all") \
                        as get_all_mock:
            get_all_mock.return_value = []
            self.assertEqual([],
                             self.manager.get_all_resources(self.context))

    def test_get_resource(self):
        expected = {'1234': {'id': '1234', "type": 'esxcluster'}}
        with mock.patch.object(self.manager._resource, "get") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'esxcluster'}}
            self.assertEqual(expected,
                             self.manager.get_resource(self.context,
                                                           '1234', False))

    def test_get_resource_with_inventory(self):
        expected = {'1234': {'id': '1234', "type": 'esxcluster'}}
        with mock.patch.object(self.manager._resource,
                               "get_with_inventory") as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'esxcluster'}}
            self.assertEqual(expected,
                             self.manager.get_resource(self.context,
                                                           '1234', True))

    def test_create_resource(self):
        expected = {'1234': {'id': '1234', "type": 'esxcluster'}}
        with mock.patch.object(self.manager._resource, "create") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'esxcluster'}}
            self.assertEqual(expected,
                            self.manager.create_resource(self.context,
                            'create_data'))

    def test_update_resource(self):
        expected = {'1234': {'id': '1234', "type": 'esxcluster'}}
        with mock.patch.object(self.manager._resource, "update") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'esxcluster'}}
            self.assertEqual(expected,
                            self.manager.update_resource(self.context,
                            "1234", 'updata_data'))

    def test_delete_resource(self):
        with mock.patch.object(self.manager._resource, "delete") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'esxcluster'}}
            self.assertTrue(self.manager.delete_resource(self.context,
                            '1234'))

    def test_update_property(self):
        expected = {'1234': {'id': '1234', "type": 'vcenter',
                             'meta_data': [{"name": "resource_id",
                                            "value": "qwerty",
                                            "id": "91"}]
                             }
                    }
        with mock.patch.object(self.manager._resource_mgr, "update_property") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter',
                                                  'meta_data': [
                                                    {"name": "resource_id",
                                                     "value": "qwerty",
                                                     "id": "91"
                                                    }]
                                                  }
                                         }
            self.assertEqual(
                expected,
                self.manager._resource_mgr.update_property(self.context,
                                                           "1234",
                                                           'resource_id',
                                                           "91"))

    def test_auto_import_resources(self):
        self.manager.context = "context"
        self.manager._worker_pool = mock.MagicMock()
        with contextlib.nested(
                            mock.patch.object(self.manager._worker_pool,
                              "spawn_n"),
                            mock.patch.object(self.manager._resource_mgr,
                              "auto_import_resources")):
            self.manager.auto_import_resources(self.context)

    def test_provision(self):
        expected = {'1234': {'id': '1234', "type": 'vcenter',
                             'meta_data': [{"name": "resource_id",
                                            "value": "qwerty",
                                            "id": "91"}]
                             }
                    }
        with mock.patch.object(self.manager._resource, "provision") \
                        as get_all_mock:
            get_all_mock.return_value = {'1234': {'id': '1234',
                                                  "type": 'vcenter',
                                                  'meta_data': [
                                                    {"name": "resource_id",
                                                     "value": "qwerty",
                                                     "id": "91"
                                                    }]
                                                  }
                                         }
            self.assertEqual(expected,
                            self.manager.provision_resource(self.context,
                            'resource_id', "91"))
