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
import copy
import eventlet

from eon.common import exception
from eon.hlm_facade.exception import NotFound as facade_not_found
from eon.common import utils
from eon.common import constants as eon_common_const
from eon.virt import manager
from eon.virt import driver
from testtools import TestCase
from eon.tests.unit import fake_data
from eon.validators import ResourceValidator as validator
from eon.virt import constants as eon_const

res_data = [{"name": "Resource-Manager1"}
           ]
res_data2 = [{"name": "Resource-Manager2",
             "id": 1234}
           ]
name = "Resource-Manager1"
name2 = "Resource-Manager2"


class Test_Validate_Names(TestCase):
    def test__validate_duplicate_names_without_id_False(self):
        self.assertFalse(manager._validate_duplicate_names(res_data, name))

    def test__validate_duplicate_names_without_id_True(self):
        self.assertTrue(manager._validate_duplicate_names(res_data2, name))

    def test__validate_duplicate_names_with_id_False_by_id(self):
        _id = 123
        self.assertFalse(manager._validate_duplicate_names(
                                            res_data2, name2, _id))

    def test__validate_duplicate_names_with_id_True_by_name(self):
        _id = 123
        self.assertTrue(manager._validate_duplicate_names(
                                            res_data2, name, _id))

    def test__validate_duplicate_names_with_id_False_by_name(self):
        _id = 123
        self.assertFalse(manager._validate_duplicate_names(
                                            res_data2, name2, _id))

    def test__validate_duplicate_names_with_id_True(self):
        _id = 1234
        self.assertTrue(manager._validate_duplicate_names(
                                            res_data2, name2, _id))


class TestManager(TestCase):

    @classmethod
    def _get_data(cls):
        data = dict(cls.data_without_meta)
        data.update({
            "meta_data": [
                cls.db_resource_mgr_pty,
            ],
        })

        return data

    @classmethod
    def setUpClass(cls):
        TestCase.setUpClass()
        manager.eon.db = mock.MagicMock()
        manager.rpcapi = mock.MagicMock()
        cls.manager = manager.ResourceManager()
        cls.context = "context"
        cls.resource_type = "vmware"

        cls.db_resource_mgr = mock.MagicMock()
        cls.db_resource = mock.MagicMock()
        cls.db_resource_mgrs = [
            cls.db_resource_mgr,
        ]
        cls.db_resources = [
            cls.db_resource,
        ]

        cls.db_resource_mgr_pty = {
            "key": "vcenter_uuid",
            "value": "vcenter-123",
            "id": "123",
        }
        cls.db_resource_ptys = [
            cls.db_resource_mgr_pty,
        ]
        cls.data_without_meta = {
            "name": "vcenter1",
            "port": "443",
            "ip_address": "10.1.192.98",
            "username": "username",
            "password": "password",
            "type": "vmware",
        }
        cls.data = cls._get_data()

    def setUp(self):
        TestCase.setUp(self)

    @classmethod
    def tearDownClass(cls):
        TestCase.tearDownClass()

    def tearDown(self):
        TestCase.tearDown(self)

    def test_start(self):
        self.assertIsNone(self.manager.start(self.context))

    def test_get_all_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_all_resource_managers=mock.DEFAULT,
                get_properties=mock.DEFAULT) as db_apis:
            db_apis['get_all_resource_managers'].return_value = \
                self.db_resource_mgrs
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_all_resource_managers.reset_mock()
            self.manager.get_all(self.context, None)

            db_api.get_all_resource_managers.assert_any_call(self.context,
                                                         types=None)

    def test_get_all_with_type_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_all_resource_managers=mock.DEFAULT,
                get_properties=mock.DEFAULT) as db_apis:
            db_apis['get_all_resource_managers'].return_value = \
                self.db_resource_mgrs
            db_apis['get_properties'].return_value = \
            self.db_resource_ptys

            db_api.get_all_resource_managers.reset_mock()
            self.manager.get_all(self.context, self.resource_type)

            types = self.resource_type.strip(",").split(",")
            db_api.get_all_resource_managers.assert_any_call(self.context,
                                                         types=types)

    def test_get_all_retrieve_error(self):
        db_api = self.manager.db_api
        with mock.patch.object(db_api, "get_all_resource_managers"):
            db_api.get_all_resource_managers = mock.MagicMock(
                                            side_effect=Exception())

            self.assertRaises(exception.RetrieveException,
                              self.manager.get_all,
                              self.context,
                              self.resource_type)

    def test_get_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_resource_manager=mock.DEFAULT,
                get_properties=mock.DEFAULT,
                ) as db_apis:
            db_apis['get_resource_manager'].return_value = self.db_resource_mgr
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_resource_manager.reset_mock()
            self.manager.get(self.context, "id")

            db_api.get_resource_manager.assert_any_call(self.context,
                                                    "id")

    def test_get_retrieve_error(self):
        db_api = self.manager.db_api
        with mock.patch.object(db_api, "get_resource_manager"):
            db_api.get_resource_manager = mock.MagicMock(
                                                side_effect=Exception())

            self.assertRaises(exception.RetrieveException,
                              self.manager.get,
                              self.context,
                              "id")

    def test_get_with_inventory_success(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_resource_manager=mock.DEFAULT,
                get_properties=mock.DEFAULT,
                ) as db_apis:
            db_apis['get_resource_manager'].return_value = self.db_resource_mgr
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_resource_manager.reset_mock()
            with mock.patch.object(driver, "load_resource_mgr_driver") \
                    as load_res_driver:
                load_res_driver.return_value = driver_obj
                driver_obj.get_inventory.return_value = mock.MagicMock()
                self.manager.get_with_inventory(self.context, "id")
                db_api.get_resource_manager.assert_any_call(self.context,
                                                    "id")

    def test_get_with_inventory_retrieve_error(self):
        db_api = self.manager.db_api
        with mock.patch.object(db_api, "get_resource_manager"):
            db_api.get_resource_manager = mock.MagicMock(
                                                side_effect=Exception())

            self.assertRaises(exception.RetrieveException,
                              self.manager.get_with_inventory,
                              self.context,
                              "id")

    def test_delete_success(self):
        act_res = [{"state": "imported"}, {"state": "imported"}]
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(db_api, "get_resource_manager"),
            mock.patch.object(self.manager, "_get_resources"),
            mock.patch.object(driver, "load_resource_mgr_driver")
                ) as (get_res, get_act_res, load_res_driver):
            get_act_res.return_value = act_res
            db_api.get_resource_manager.return_value = self.db_resource_mgr
            load_res_driver.return_value = driver_obj
            driver_obj.validate_delete.return_value = mock.MagicMock()
            db_api.delete_resource_manager.reset_mock()
            self.manager.delete(self.context, "id")
            db_api.delete_resource_manager.assert_any_call(self.context,
                                                       "id")

    def test_delete_failure(self):
        act_res = [{"state": "activated"}, {"state": "imported"}]
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(db_api, "get_resource_manager"),
            mock.patch.object(driver, "load_resource_mgr_driver"),
            mock.patch.object(self.manager, "_get_resources"),
                ) as (get_res, load_res_driver, get_act_res):
            load_res_driver.return_value = driver_obj
            get_res.return_value = self.db_resource_mgr
            get_act_res.return_value = act_res
            self.assertRaises(exception.DeleteException, self.manager.delete,
                              self.context, "id")

    def test_create_success(self):
        resource_ptys = {"vcenter_uuid": "vcenter-123"}
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(utils, "get_addresses"),
            mock.patch.object(driver, "load_resource_mgr_driver"),
            mock.patch.object(db_api, "create_resource_manager"),
            mock.patch.object(db_api, "create_property"),
                ) as (get_addr, load_res_driver, create_res_mgr,
                      create_prop):
            get_addr.return_value = ["10.1.214.16"]
            load_res_driver.return_value = driver_obj
            driver_obj.validate_create.return_value = mock.MagicMock()
            driver_obj.get_properties.return_value = resource_ptys
            create_res_mgr.return_value = self.db_resource_mgr
            self.manager.create(self.context, self.data)

    def test_create_internal_error(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(utils, "get_addresses"),
            mock.patch.object(driver, "load_resource_mgr_driver"),
            mock.patch.object(db_api, "create_resource_manager"),
                 ) as (get_addr, load_res_driver, create_res_mgr):
            get_addr.return_value = ["10.1.214.16"]
            load_res_driver.return_value = driver_obj
            db_api.create_resource_manager = mock.MagicMock(
                side_effect=Exception())
            self.assertRaises(exception.CreateException,
                                  self.manager.create,
                                  self.context,
                                  self.data)

    def test_update_success(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(utils, "get_addresses"),
            mock.patch.object(driver, "load_resource_mgr_driver"),
            mock.patch.object(db_api, "update_resource_manager"),
            mock.patch.object(self.manager, "_is_creds_changed"),
            mock.patch.object(self.manager, "_get_resources"),
            mock.patch.object(eventlet, "spawn_n", return_value=True),
                ) as (get_addr, load_res_driver, update_res_mgr,
                      m_creds_change, m_get_res,
                      spawn_m):
            get_addr.return_value = ["10.1.214.16"]
            load_res_driver.return_value = driver_obj
            driver_obj.validate_update.return_value = mock.MagicMock()
            update_res_mgr.return_value = self.db_resource_mgr
            resource_mgr_dict = manager._make_response(self.db_resource_mgr)
            m_get_res.return_value = resource_mgr_dict
            self.data.update({'run_playbook': True})
            self.manager.update(self.context, fake_data.fake_id1, self.data)
            spawn_m.assert_called_once_with(driver_obj.update,
                                       self.context, fake_data.fake_id1,
                                       resource_inventory=resource_mgr_dict)

    def test_update_success_run_playbook_false(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(utils, "get_addresses"),
            mock.patch.object(driver, "load_resource_mgr_driver"),
            mock.patch.object(db_api, "update_resource_manager"),
            mock.patch.object(self.manager, "_is_creds_changed",
                              return_value=False),
            mock.patch.object(eventlet, "spawn_n"),
                ) as (get_addr, load_res_driver, update_res_mgr,
                      m_creds_change,
                      spawn_m):
            get_addr.return_value = ["10.1.214.16"]
            load_res_driver.return_value = driver_obj
            driver_obj.validate_update.return_value = mock.MagicMock()
            update_res_mgr.return_value = self.db_resource_mgr
            self.data.update({'run_playbook': False})
            self.manager.update(self.context, fake_data.fake_id1, self.data)
            spawn_m.assert_not_called()

    def test_update_internal_error(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(utils, "get_addresses"),
            mock.patch.object(driver, "load_resource_mgr_driver"),
            mock.patch.object(db_api, "update_resource_manager")
                ) as (get_addr, load_res_driver, update_res_mgr):
            get_addr.return_value = ["10.1.214.16"]
            load_res_driver.return_value = driver_obj
            db_api.update_resource_manager = mock.MagicMock(
                side_effect=Exception())
            driver_obj.validate_update.return_value = mock.MagicMock()
            update_res_mgr.return_value = self.db_resource_mgr
            self.assertRaises(exception.UpdateException,
                              self.manager.update,
                              self.context,
                              "id", self.data)

    def test_auto_import_resources(self):
        db_api = self.manager.db_api
        driver_obj = mock.MagicMock()
        new = [('domain-c1998', 'esx-app-cluster1')]
        rem = [('domain-c1999', 'esx-app-cluster2')]
        with mock.patch.multiple(
                db_api,
                get_all_resource_managers=mock.DEFAULT,
                get_all_resources=mock.DEFAULT,
                get_properties=mock.DEFAULT
                ) as db_apis:
            db_apis['get_all_resource_managers'].return_value = \
                            self.db_resource_mgrs
            db_apis['get_all_resources'].return_value = \
                self.db_resources
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys
            with mock.patch.object(driver, "load_resource_mgr_driver") \
                    as load_res_driver:
                load_res_driver.return_value = driver_obj
                driver_obj.poll_resources.return_value = (new, rem)
                self.manager.auto_import_resources(self.context, "type")


class TestResources(TestCase):

    @classmethod
    def _get_data(cls):
        data = dict(cls.data_without_meta)
        data.update({
            "meta_data": [
                cls.db_resource_pty,
            ],
        })

        return data

    @classmethod
    def setUpClass(cls):
        TestCase.setUpClass()
        manager.eon.db = mock.MagicMock()
        manager.rpcapi = mock.MagicMock()
        cls.manager = manager.Resource()
        cls.context = "context"
        cls.resource_type = "vmware"
        cls.resource_state = "imported"

        cls.db_resource = mock.MagicMock()
        cls.db_resources = [
            cls.db_resource,
        ]

        cls.db_resource_pty = {
            "key": "vcenter_uuid",
            "value": "vcenter-123",
            "id": "123",
        }
        cls.db_resource_ptys = [
            cls.db_resource_pty,
        ]
        cls.data_without_meta = {
            "name": "vcenter1",
            "port": "443",
            "ip_address": "10.1.192.98",
            "username": "username",
            "password": "password",
            "type": "vmware",
        }
        cls.data = cls._get_data()

    def setUp(self):
        TestCase.setUp(self)
        manager.eon.db = mock.MagicMock()
        self.mocked_obj = mock.Mock()

    def test_get_all_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_all_resources=mock.DEFAULT,
                get_properties=mock.DEFAULT) as db_apis:
            db_apis['get_all_resources'].return_value = \
                self.db_resources
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_all_resources.reset_mock()
            filters = {"type": None, "state": None}
            self.manager.get_all(self.context, filters=filters)

            db_api.get_all_resources.assert_any_call(self.context,
                                                     type=None, state=None)

    def test_get_all_with_type_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_all_resources=mock.DEFAULT,
                get_properties=mock.DEFAULT) as db_apis:
            db_apis['get_all_resources'].return_value = \
                self.db_resources
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_all_resources.reset_mock()
            filters = {"type": self.resource_type, "state": None}
            self.manager.get_all(self.context, filters=filters)

            db_api.get_all_resources.assert_any_call(self.context,
                                                     type=self.resource_type,
                                                     state=None)

    def test_get_all_with_state_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_all_resources=mock.DEFAULT,
                get_properties=mock.DEFAULT) as db_apis:
            db_apis['get_all_resources'].return_value = \
                self.db_resources
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_all_resources.reset_mock()
            filters = {"type": None, "state": self.resource_state}
            self.manager.get_all(self.context, filters=filters)

            db_api.get_all_resources.assert_any_call(self.context,
                                                     type=None,
                                                     state=self.resource_state)

    def test_get_all_with_type_state_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_all_resources=mock.DEFAULT,
                get_properties=mock.DEFAULT) as db_apis:
            db_apis['get_all_resources'].return_value = \
                self.db_resources
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_all_resources.reset_mock()
            filters = {"type": self.resource_type,
                       "state": self.resource_state}
            self.manager.get_all(self.context, filters=filters)

            db_api.get_all_resources.assert_any_call(self.context,
                                                     type=self.resource_type,
                                                     state=self.resource_state)

    def test_get_all_retrieve_error(self):
        db_api = self.manager.db_api
        with mock.patch.object(db_api, "get_all_resources"):
            db_api.get_all_resources = mock.MagicMock(
                                            side_effect=Exception())
            filters = {"type": self.resource_type}
            self.assertRaises(exception.RetrieveException,
                              self.manager.get_all,
                              self.context,
                              filters)

    def test_get_success(self):
        db_api = self.manager.db_api
        with mock.patch.multiple(
                db_api,
                get_resource=mock.DEFAULT,
                get_properties=mock.DEFAULT,
                ) as db_apis:
            db_apis['get_resource'].return_value = self.db_resource
            db_apis['get_properties'].return_value = \
                self.db_resource_ptys

            db_api.get_resource.reset_mock()
            self.manager.get(self.context, "id")

            db_api.get_resource.assert_any_call(self.context,
                                                    "id")

    def test_get_retrieve_error(self):
        db_api = self.manager.db_api
        with mock.patch.object(db_api, "get_resource"):
            db_api.get_resource = mock.MagicMock(
                                                side_effect=Exception())

            self.assertRaises(exception.RetrieveException,
                              self.manager.get,
                              self.context,
                              "id")

    def test_get_with_inventory(self):
        with contextlib.nested(
            mock.patch.object(self.manager.db_api, "get_resource"),
            mock.patch.object(self.manager.db_api, "get_properties"),
            mock.patch.object(self.manager.db_api,
                              "get_resource_managers_by_resource_id"),
            mock.patch.object(driver, "load_resource_driver")
                               ) as (get_res, get_prop,
                                     get_res_mgr_by_id, load_res_dr):
            load_res_dr.return_value = self.mocked_obj
            self.mocked_obj.get_res_inventory = fake_data.get_res_fake_inv
            get_res.return_value = fake_data.res_data_db_cluster
            get_prop.return_value = fake_data.get_res_properties_cluster
            get_res_mgr_by_id.return_value = fake_data.res_mgr_data1
            resultant_dict = fake_data.get_with_inventory_cluster
            resultant_dict.update({"inventory":
                    fake_data.get_res_fake_inv(mock.ANY, mock.ANY)})

            observed = self.manager.get_with_inventory(self.context,
                                                   fake_data.fake_id1)
            self.assertEqual(resultant_dict, observed)

    def test_get_with_inventory_not_found(self):
        with mock.patch.object(self.manager.db_api, "get_resource",
                               ) as get_res:
            get_res.side_effect = exception.NotFound
            self.assertRaises(exception.NotFound,
                self.manager.get_with_inventory, self.context,
                fake_data.fake_id1)

    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'commit_changes')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'delete_server')
    def test_delete_success(self, mock_ds, mock_cc):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with mock.patch.object(db_api, "get_resource"):
            db_api.get_resource.return_value = self.db_resource
            db_api.delete_resource.reset_mock()
            with mock.patch.object(driver, "load_resource_driver") \
                    as load_res_driver:
                load_res_driver.return_value = driver_obj
                driver_obj.validate_delete.return_value = mock.MagicMock()
                self.manager.delete(self.context, "id")
                db_api.delete_resource.assert_any_call(self.context,
                                                       "id")

    def test_delete_failure(self):
        res = {'type': "esxcluster"}
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(db_api, "get_resource"),
            mock.patch.object(driver, "load_resource_driver"),
                ) as (get_res, load_res_driver):
            get_res.return_value = res
            load_res_driver.return_value = driver_obj
            driver_obj.validate_delete.return_value = mock.MagicMock()
            self.assertRaises(exception.DeleteException, self.manager.delete,
                               self.context, "id")

    def test_create_success(self):
        resource_ptys = {"vcenter_uuid": "vcenter-123"}
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(utils, "get_addresses"),
            mock.patch.object(driver, "load_resource_driver"),
            mock.patch.object(db_api, "create_resource"),
            mock.patch.object(db_api, "create_property"),
                ) as (get_addr, load_res_driver, create_res,
                      create_prop):
            get_addr.return_value = ["10.1.214.16"]
            load_res_driver.return_value = driver_obj
            driver_obj.validate_create.return_value = mock.MagicMock()
            driver_obj.get_properties.return_value = resource_ptys
            create_res.return_value = self.db_resource
            self.manager.create(self.context, self.data)

    def test_create_internal_error(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(utils, "get_addresses"),
            mock.patch.object(driver, "load_resource_mgr_driver"),
            mock.patch.object(db_api, "create_resource"),
                 ) as (get_addr, load_res_driver, create_res):
            get_addr.return_value = ["10.1.214.16"]
            load_res_driver.return_value = driver_obj
            db_api.create_resource = mock.MagicMock(
                side_effect=Exception())
            self.assertRaises(exception.CreateException,
                                  self.manager.create,
                                  self.context,
                                  self.data)

    def test__activate(self):
        activate_data = {"network_properties": "network_json"}
        resource_mgr_data = {"type": "esxcluster",
                "id": "1234", "state": "imported"}
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with mock.patch.object(self.manager, "get_with_inventory"):
            self.manager.get_with_inventory.return_value = resource_mgr_data
            with contextlib.nested(
                mock.patch.object(driver, "load_resource_driver"),
                mock.patch.object(db_api, "update_resource")
                     ) as (load_res_driver, update_res):
                load_res_driver.return_value = driver_obj
                driver_obj.set_network_properties.return_value = \
                                                    mock.MagicMock()
                driver_obj.provision.return_value = mock.MagicMock()
                driver_obj.build_input_model_data.return_value = (
                                                    mock.MagicMock())
                self.manager._activate(self.context, "id_",
                                       resource_mgr_data,
                                       activate_data)

    def test__activate_exception(self):
        activate_data = {"network_properties": "network_json"}
        resource_mgr_data = {"type": "esxcluster",
                "id": "1234", "state": "imported"}
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with mock.patch.object(self.manager, "get_with_inventory"):
            self.manager.get_with_inventory.return_value = resource_mgr_data
            with contextlib.nested(
                mock.patch.object(driver, "load_resource_driver"),
                mock.patch.object(db_api, "update_resource")
                     ) as (load_res_driver, _):
                load_res_driver.return_value = driver_obj
                driver_obj.set_network_properties.return_value = \
                                                    mock.MagicMock()
                driver_obj.provision.return_value = mock.MagicMock()
                driver_obj.build_input_model_data.return_value = (
                                                    mock.MagicMock())
                driver_obj.activate.side_effect = Exception()

                self.assertRaises(exception.ActivationFailure,
                                  self.manager._activate,
                                  self.context,
                                  "id_",
                                  resource_mgr_data,
                                  activate_data)

    @mock.patch('eon.db.sqlalchemy.api_v2.delete_property')
    def test__activate_exception_delete_resource(self, mocked_delete):
        activate_data = {"network_properties": "network_json"}
        resource_mgr_data = {"type": "esxcluster",
                "id": "1234", "state": "imported"}
        mocked_delete.side_effect = [exception.NotFound]
        self.assertRaises(exception.ActivationFailure,
                          self.manager._activate,
                          self.context,
                          "id_",
                          resource_mgr_data,
                          activate_data)

    def test_activate_exception(self):
        resource_mgr_data = {"type": "esxcluster",
                "id": "1234", "state": "imported"}
        activate_data = {"network_properties": "network_json"}
        with contextlib.nested(
            mock.patch.object(self.manager, "get_with_inventory"),
            mock.patch.object(eventlet, "spawn_n")
                               ) as (get_with_in, _):
            get_with_in.return_vale = resource_mgr_data
            self.assertRaises(Exception,
                self.manager.activate, self.context, "id_",
                activate_data)

    def test_activate_type_exception(self):
        resource_mgr_data = {"type": "unsupported",
                "id": "1234", "state": "imported"}
        activate_data = {"network_properties": "network_json"}
        with contextlib.nested(
            mock.patch.object(self.manager, "get_with_inventory"),
            mock.patch.object(eventlet, "spawn_n")
                               ) as (get_with_in, _):
            get_with_in.return_vale = resource_mgr_data
            self.assertRaises(Exception,
                validator.validate_type, resource_mgr_data['type'],
                eon_common_const.ResourceConstants.SUPPORTED_TYPES)

    def test__host_commission_exception(self):
        driver_obj = mock.MagicMock()
        get_net_m = fake_data.network_prop
        build_input_model_data_for_new_hosts = mock.MagicMock()
        with contextlib.nested(
                mock.patch.object(driver, "load_resource_driver")):
            driver_obj.get_network_properties.return_value = get_net_m
            driver_obj.host_commission.return_value = {}
            driver_obj.build_input_model_data_for_new_hosts = (
                build_input_model_data_for_new_hosts)
            build_input_model_data_for_new_hosts.side_effect = Exception("")
            self.manager._host_commission(self.context, fake_data.fake_id1,
                                          fake_data.cluster_data_remove,
                                          {})

    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    def test_host_commission(self, mock_state):
        data = {"server_group": "RACK-1"}
        res_inv = copy.deepcopy(fake_data.resource_inventory)
        with contextlib.nested(
            mock.patch.object(self.manager, "get_with_inventory",
                              return_value = res_inv),
            mock.patch.object(eventlet, "spawn_n"),
            ) as (get_with, spawn_m):
            self.manager.host_commission(self.context, fake_data.fake_id1,
                                         data)
            mock_state.assert_called_once_with(self.context,
                fake_data.fake_id1, 'state',
                eon_const.RESOURCE_STATE_HOST_COMMISSION_INITIATED)
            spawn_m.assert_called_once_with(self.manager._host_commission,
                                            self.context, fake_data.fake_id1,
                                            res_inv,
                                            data)
            get_with.assert_called_once_with(self.context, fake_data.fake_id1)

    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    def test_deactivate(self, mock_state):
        self.context = mock.MagicMock()
        data = {}
        res_inv = copy.deepcopy(fake_data.resource_inventory1)
        driver_obj = mock.MagicMock()
        with contextlib.nested(
            mock.patch.object(driver, "load_resource_driver"),
            mock.patch.object(self.manager, "get_with_inventory",
                              return_value=res_inv),
            mock.patch.object(eventlet, "spawn_n"),
            ) as (res_driver, _, spawn_m):
            res_driver.return_value = driver_obj
            self.manager.deactivate(self.context, fake_data.fake_id1, data)
            spawn_m.assert_called_once_with(self.manager._deactivate,
                self.context, fake_data.fake_id1,
                data, res_inv)
        mock_state.called_once_with(self.context, fake_data.fake_id1,
                                    'state',
                                    eon_const.EON_RESOURCE_STATE_DEACTIVATING)

    def test_update_success_no_creds_change(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(driver, "load_resource_driver"),
            mock.patch.object(db_api, "update_resource"),
            mock.patch.object(self.manager, "_is_creds_changed")
                ) as (load_res_driver, update_res, is_creds):
            load_res_driver.return_value = driver_obj
            driver_obj.validate_update.return_value = mock.MagicMock()
            driver_obj.update.return_value = mock.MagicMock()
            update_res.return_value = self.db_resource
            is_creds.return_value = False
            self.manager.update(self.context, "id", self.data)
            assert driver_obj.validate_update.call_count == 0
            assert driver_obj.update.call_count == 0

    def test_update_success_creds_changed(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(db_api, "get_resource"),
            mock.patch.object(driver, "load_resource_driver"),
            mock.patch.object(db_api, "update_resource"),
            mock.patch.object(manager, "_make_response"),
            mock.patch.object(self.manager, "_is_creds_changed")
                ) as (get_res, load_res_driver, update_res, make_resp,
                      is_creds):
            load_res_driver.return_value = driver_obj
            driver_obj.update.return_value = mock.MagicMock()
            driver_obj.validate_update.return_value = mock.MagicMock()
            db_res_data = copy.deepcopy(fake_data.hyperv_resource_inventory)
            get_res.return_value = db_res_data
            update_res.return_value = self.db_resource
            db_res_data['state'] = "activated"
            make_resp.return_value = db_res_data
            is_creds.return_value = True
            self.manager.update(self.context, "id", self.data)
            driver_obj.update.assert_called_once_with(
                    self.context, self.db_resource, "id")

    def test_update_exception_creds_changed(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(db_api, "get_resource"),
            mock.patch.object(driver, "load_resource_driver"),
            mock.patch.object(db_api, "update_resource"),
            mock.patch.object(manager, "_make_response"),
            mock.patch.object(self.manager, "_is_creds_changed")
                ) as (get_res, load_res_driver, update_res, make_resp,
                      is_creds):
            load_res_driver.return_value = driver_obj
            driver_obj.update.side_effect = Exception()
            driver_obj.validate_update.return_value = mock.MagicMock()
            db_res_data = copy.deepcopy(fake_data.hyperv_resource_inventory)
            get_res.return_value = db_res_data
            update_res.return_value = self.db_resource
            db_res_data['state'] = "activated"
            make_resp.return_value = db_res_data
            is_creds.return_value = True
            self.assertRaises(exception.UpdateException,
                              self.manager.update,
                              self.context,
                              "id", self.data)
            driver_obj.update.assert_called_once_with(
                    self.context, self.db_resource, "id")

    def test_update_internal_error(self):
        driver_obj = mock.MagicMock()
        db_api = self.manager.db_api
        with contextlib.nested(
            mock.patch.object(driver, "load_resource_driver"),
            mock.patch.object(db_api, "update_resource")
                ) as (load_res_driver, update_res):
            load_res_driver.return_value = driver_obj
            db_api.update_resource = mock.MagicMock(
                                                    side_effect=Exception())
            driver_obj.validate_update.return_value = mock.MagicMock()
            update_res.return_value = self.db_resource
            self.assertRaises(exception.UpdateException,
                              self.manager.update,
                              self.context,
                              "id", self.data)

    def test_provision(self):
        provision_data = {"type": "hlinux"}
        resource_data = {"type": "baremetal",
                "id": "1234", "state": "imported"}
        with contextlib.nested(
                               mock.patch.object(self.manager,
                                                 "get_with_inventory"),
                               mock.patch.object(eventlet, "spawn_n")
                               ) as (get_inv, _):
            get_inv.return_value = resource_data
            self.manager.provision(self.context,
                                   "id_",
                                   provision_data)

    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.cobbler_deploy_status")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.cobbler_deploy")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.get_server_by_id")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.get_server_groups")
    @mock.patch("eon.virt.common.utils.get_hypervisor_roles")
    def test__provision(self, m_get_roles, m_get_groups, m_get_server_id,
                        m_cobb_dep, m_cobb_status, m_update_pop):
        provision_data = {"type": "hlinux"}
        m_get_roles.return_value = ["KVM-COMPUTE-ROLE"]
        m_get_groups.return_value = fake_data.fake_server_groups
        context = fake_data.FakeContext()
        self.manager._provision(context, "_id_", provision_data,
                                fake_data.baremetal_resource_data)
        m_get_server_id.assert_called_once_with("baremetal-node")
        m_cobb_dep.assert_called_once_with("baremetal-node", "password")
        m_cobb_status.assert_called_once_with("baremetal-node")
        calls = [mock.call(context, "baremetal-node",
                           eon_const.EON_RESOURCE_STATE,
                           eon_const.EON_RESOURCE_STATE_PROVISIONING),
                 mock.call(context, "baremetal-node",
                           eon_const.EON_RESOURCE_STATE,
                           eon_const.EON_RESOURCE_STATE_PROVISIONED)]
        m_update_pop.has_calls(calls)

    @mock.patch('eon.virt.common.utils.VirtCommonUtils.update_prop')
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.cobbler_deploy_status")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.cobbler_deploy")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.config_processor_run")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.commit_changes")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.create_server")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.get_server_by_id")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.get_server_groups")
    @mock.patch("eon.virt.common.utils.get_hypervisor_roles")
    def test__provision_not_found(self, m_get_roles, m_get_groups,
                                  m_get_server_id, m_create_server,
                                  m_commit_changes, mock_cp_run, m_cobb_dep,
                                  m_cobb_status, m_update_pop):
        provision_data = {"type": "hlinux"}
        m_get_roles.return_value = ["KVM-COMPUTE-ROLE-BOND-2DISKS"]
        m_get_groups.return_value = fake_data.fake_server_groups
        context = fake_data.FakeContext()
        m_get_server_id.side_effect = [facade_not_found]
        self.manager._provision(context, "_id_", provision_data,
                                fake_data.baremetal_resource_data)
        m_get_server_id.assert_called_once_with("baremetal-node")
        expected_model = {'ip-addr': '10.10.10.10', 'server-group': 'RACK1',
                          'role': 'KVM-COMPUTE-ROLE-BOND-2DISKS',
                          'id': 'baremetal-node'}
        m_create_server.assert_called_once_with(expected_model)
        m_commit_changes.assert_called_once_with(
            "baremetal-node", 'Provision KVM compute resource')
        mock_cp_run.assert_called_once_with()
        m_cobb_dep.assert_called_once_with("baremetal-node", "password")
        m_cobb_status.assert_called_once_with("baremetal-node")
        calls = [mock.call(context, "baremetal-node",
                           eon_const.EON_RESOURCE_STATE,
                           eon_const.EON_RESOURCE_STATE_PROVISIONING),
                 mock.call(context, "baremetal-node",
                           eon_const.EON_RESOURCE_STATE,
                           eon_const.EON_RESOURCE_STATE_PROVISIONED)]
        m_update_pop.has_calls(calls)

    def test__provision_exception(self):
        driver_obj = mock.MagicMock()
        provision_data = {"type": "hlinux"}
        with mock.patch.object(driver,
                               "load_resource_driver") as load_res_driver:
            load_res_driver.return_value = driver_obj
            self.assertRaises(AttributeError, self.manager._provision,
                              self.context, "_id_", provision_data,
                              fake_data.baremetal_resource_data)

    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.run_playbook")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.config_processor_run")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.commit_changes")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.delete_server")
    @mock.patch("eon.hlm_facade.hlm_facade_handler."
                "HLMFacadeWrapper.revert_changes")
    def test__provision_exception2(self, mock_revert,
                                   mock_delete, mock_commit,
                                   mock_cp_run, mock_cobbler_remove):
        driver_obj = mock.MagicMock()
        provision_data = {"type": "hlinux"}
        with mock.patch.object(driver,
                               "load_resource_driver") as load_res_driver:
            load_res_driver.return_value = driver_obj
            resource_id = fake_data.baremetal_resource_data.get('id')
            self.manager._provision(self.context, "_id_", provision_data,
                                    fake_data.baremetal_resource_data)
            mock_revert.assert_called_once_with()
            mock_delete.assert_called_once_with(resource_id)
            mock_commit.assert_called_once_with(
                resource_id, 'Delete KVM compute resource')
            mock_cp_run.assert_called_once_with()
            extra_args = {"extraVars": {
                "nodename": "_id_"
            }}
            mock_cobbler_remove.assert_called_once_with(
                "hlm_remove_cobbler_node", extra_args=extra_args)

    def test_forced_deactivate(self):
        data = {'forced': True}
        res_inv = copy.deepcopy(fake_data.resource_inventory)
        with contextlib.nested(
            mock.patch.object(self.manager, "get_with_inventory",
                              return_value=res_inv),
            mock.patch.object(eventlet, "spawn_n"),
            mock.patch.object(self.manager, "_pre_deactivation_steps"),
            ) as (_, spawn_m, pre_deactivation_steps):
            self.manager.deactivate(self.context, fake_data.fake_id1, data)
            pre_deactivation_steps.assert_not_called()
            spawn_m.assert_called_once_with(self.manager._deactivate,
                self.context, fake_data.fake_id1,
                data, res_inv)
