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
import copy
import json
import mock

from eon.virt.vmware import driver
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
from eon.deployer import driver as net_driver
from eon.virt import constants
from eon.virt.vmware import constants as vmware_const


class TestVMwareVCDriver(base_test.TestCase):
    def setUp(self):
        base_test.TestCase.setUp(self)
        self.vmware_driv = driver.VMwareVCDriver()
        self.resource_type = constants.EON_RESOURCE_TYPE_ESX_CLUSTER
        self.session_mock = mock.MagicMock()
        self.mocked_obj = mock.Mock()

    def test_set_network_properties_with_no_net_prop_act_in_progress(self):
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "activation_in_progress_per_dc"),
            mock.patch.object(self.vmware_driv, "_store_and_setup_network"),
            mock.patch.object(self.vmware_driv, "get_network_properties"),
                               ) as (activation_in, _store_mock, get_net):
            get_net.return_value = self.mocked_obj
            ret = self.vmware_driv.set_network_properties(self.context,
                                self.resource_type,
                                fake_data.get_with_inventory_cluster,
                                {})
            self.assertEqual(activation_in.call_count, 3)
            activation_in.assert_called_with(self.context,
                fake_data.get_with_inventory_cluster)
            assert not _store_mock.called
            self.assertEqual(ret, self.mocked_obj)

    def test_set_network_properties_with_net_prop_act_in_progress(self):
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "activation_in_progress_per_dc"),
            mock.patch.object(self.vmware_driv, "_store_and_setup_network"),
                               ) as (activation_in, _store_mock):
            self.vmware_driv.set_network_properties(self.context,
                    self.resource_type,
                    fake_data.get_with_inventory_cluster,
                    fake_data.network_prop)
            activation_in.assert_called_once_with(self.context,
                fake_data.get_with_inventory_cluster)

            _store_mock.assert_called_once_with(self.context,
                                self.resource_type,
                                fake_data.get_with_inventory_cluster,
                                fake_data.network_prop,
                                set_network=True)

    def test_set_network_properties_with_net_prop_act_not_in_progress(self):
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "activation_in_progress_per_dc"),
            mock.patch.object(self.vmware_driv, "_store_and_setup_network"),
                               ) as (activation_in, _store_mock):
            activation_in.return_value = False
            self.vmware_driv.set_network_properties(self.context,
                    self.resource_type,
                    fake_data.get_with_inventory_cluster,
                    fake_data.network_prop)
            self.assertEqual(2, activation_in.call_count)
            activation_in.assert_called_with(self.context,
                fake_data.get_with_inventory_cluster)

            _store_mock.assert_called_once_with(self.context,
                                self.resource_type,
                                fake_data.get_with_inventory_cluster,
                                fake_data.network_prop,
                                set_network=True,
                                store_dc_level=True
                                )

    def test_set_network_properties_with_net_prop_none(self):
        cluster_data = copy.deepcopy(fake_data.get_with_inventory_cluster)
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "activation_in_progress_per_dc"),
            mock.patch.object(self.vmware_driv, "_store_and_setup_network"),
            mock.patch.object(self.vmware_driv, "get_network_properties"),
                               ) as (activation_in, _store_mock, get_ne):
            activation_in.return_value = False
            self.vmware_driv.set_network_properties(self.context,
                    self.resource_type,
                    cluster_data,
                    {})
            get_ne.assert_called_once_with(self.context,
                cluster_data['resource_manager_info'], cluster_data)
            assert not _store_mock.called

    def test_set_network_properties_with_net_prop_none_excep(self):
        cluster_data = copy.deepcopy(fake_data.get_with_inventory_cluster)
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "activation_in_progress_per_dc"),
            mock.patch.object(self.vmware_driv, "_store_and_setup_network"),
            mock.patch.object(self.vmware_driv, "get_network_properties"),
                               ) as (activation_in, _store_mock, get_ne):
            get_ne.return_value = None
            activation_in.return_value = False
            self.assertRaises(Exception,
                self.vmware_driv.set_network_properties,
                self.context,
                self.resource_type,
                cluster_data,
                    {})

    def test_delete_network_properties(self):
        cluster_data = copy.deepcopy(fake_data.get_with_inventory_cluster)
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "is_last_cluster_per_dc"),
            mock.patch.object(self.vmware_driv,
                "_delete_and_teardown_network"),
            mock.patch.object(self.vmware_driv, "get_network_properties"),
                               ) as (is_last, _store_mock, get_net):
            self.vmware_driv.delete_network_properties(self.context,
                                                       cluster_data)
            is_last.assert_called_once_with(self.context, cluster_data)
            get_net.assert_called_once_with(self.context,
                cluster_data['resource_manager_info'], cluster_data)

    def test_delete_network_properties_net_prop_none(self):
        cluster_data = copy.deepcopy(fake_data.get_with_inventory_cluster)
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "is_last_cluster_per_dc"),
            mock.patch.object(self.vmware_driv,
                "_delete_and_teardown_network"),
            mock.patch.object(self.vmware_driv, "get_network_properties"),
                               ) as (is_last, _store_mock, get_net):
            get_net.return_value = None
            self.vmware_driv.delete_network_properties(self.context,
                                                       cluster_data)
            is_last.assert_called_once_with(self.context, cluster_data)
            get_net.assert_called_once_with(self.context,
                cluster_data['resource_manager_info'], cluster_data)

    def test_delete_network_properties_not_last_cluster_1(self):
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "is_last_cluster_per_dc"),
            mock.patch.object(self.vmware_driv,
                              "_delete_and_teardown_network"),
            mock.patch.object(self.vmware_driv,
                              "get_cluster_network_properties",
                              return_value=fake_data.cluster_net_prop),
            mock.patch.object(self.vmware_driv,
                              "get_network_properties"),
                               ) as (is_last, _delete_mock, get_cls_net,
                                     get_net_prop):
            is_last.return_value = False
            self.vmware_driv.delete_network_properties(self.context,
                                                       cluster_data)
            is_last.assert_called_once_with(self.context, cluster_data)
            get_cls_net.assert_called_once_with(self.context,
                cluster_data["id"])
            get_net_prop.assert_called_once_with(self.context,
                cluster_data['resource_manager_info'], cluster_data)
            _delete_mock.assert_called_once_with(self.context, cluster_data,
                                                 fake_data.cluster_net_prop,
                delete_cluster_level=True,
                delete_dc_level=False, tear_down_network=True)

    def test_delete_network_properties_not_last_cluster_2(self):
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        with contextlib.nested(
            mock.patch.object(self.vmware_driv,
                              "is_last_cluster_per_dc"),
            mock.patch.object(self.vmware_driv,
                              "_delete_and_teardown_network"),
            mock.patch.object(self.vmware_driv,
                              "get_cluster_network_properties",
                              return_value=fake_data.cluster_net_prop),
            mock.patch.object(self.vmware_driv,
                              "get_network_properties",
                              return_value=fake_data.network_prop1),
                               ) as (is_last, _delete_mock, get_cls_net,
                                     get_net_prop):
            is_last.return_value = False
            self.vmware_driv.delete_network_properties(self.context,
                                                       cluster_data)
            is_last.assert_called_once_with(self.context, cluster_data)
            get_cls_net.assert_called_once_with(self.context,
                cluster_data["id"])
            get_net_prop.assert_called_once_with(self.context,
                cluster_data['resource_manager_info'], cluster_data)
            _delete_mock.assert_called_once_with(self.context, cluster_data,
                    fake_data.cluster_net_prop,
                delete_cluster_level=True,
                delete_dc_level=False, tear_down_network=False)

    def test__store_and_setup_network(self):
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        network_prop = {}
        with contextlib.nested(
            mock.patch.object(self.vmware_driv.db_api,
                              "get_transactional_session"),
            mock.patch.object(self.vmware_driv.db_api, "create_property"),
                               ) as (_, _):
            self.vmware_driv._store_and_setup_network(self.context,
                self.resource_type, cluster_data, network_prop)

    def test__store_and_setup_network_with_dc_level(self):
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        network_prop = {}
        with contextlib.nested(
            mock.patch.object(self.vmware_driv.db_api,
                              "get_transactional_session"),
            mock.patch.object(self.vmware_driv, "store_network_dc_level"),
            mock.patch.object(self.vmware_driv.db_api, "create_property"),
                               ) as (transac_session, store_net, _):
            transac_session.return_value = self.session_mock
            self.vmware_driv._store_and_setup_network(self.context,
                self.resource_type, cluster_data, network_prop,
                store_dc_level=True)
            store_net.assert_called_once_with(self.context, cluster_data,
                                              "dc-1",
                                              network_prop,
                                              self.session_mock)

    def test__store_and_setup_network_with_set_network(self):
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        network_prop = {}
        with contextlib.nested(
            mock.patch.object(self.vmware_driv.db_api,
                              "get_transactional_session"),
            mock.patch.object(net_driver, "load_resource_network_driver"),
            mock.patch.object(self.vmware_driv.db_api, "create_property"),
                               ) as (transac_session, _, _):
            transac_session.return_value = self.session_mock
            self.vmware_driv._store_and_setup_network(self.context,
                self.resource_type, cluster_data, network_prop,
                set_network=True)

    def test_get_cluster_network_properties(self):
        cluster_id = fake_data.fake_id1
        network_prop = [mock.Mock()]
        network_prop[0].value = json.dumps(fake_data.network_prop)
        with mock.patch.object(self.vmware_driv.db_api,
                               "get_properties") as db:
            db.return_value = network_prop
            self.vmware_driv.get_cluster_network_properties(
                                    self.context, cluster_id)
            db.assert_called_once_with(self.context,
                    cluster_id, key=vmware_const.NET_PROPS)

    def test__delete_and_teardown_network(self):
        cluster_data = copy.deepcopy(fake_data.cluster_data_remove)
        network_property = fake_data.network_prop
        with mock.patch.object(net_driver,
                               "load_resource_network_driver") as net_:
            net_.return_value = self.mocked_obj
            mock.patch.object(self.mocked_obj, "teardown_network")
            self.vmware_driv._delete_and_teardown_network(self.context,
                cluster_data, network_property, tear_down_network=True)
