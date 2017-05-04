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

import mock

from eon.common import rpc
from eon.conductor.v2 import rpcapi as conductor_rpcapi
from eon.tests.unit import base_test

import oslo_messaging

class TestConductorAPI(base_test.TestCase):

    @mock.patch('oslo_messaging.get_transport')
    def setUp(self, mock_transport):
        base_test.TestCase.setUp(self)
        conductor_rpcapi.proxy = mock.MagicMock()
        conf = mock.MagicMock()
        conf.transport_url = "rabbit://me:passwd@host:5672/virtual_host"
        rpc.init(conf)
        self.rpcapi = conductor_rpcapi.ConductorAPI(topic="fake-topic")

    def _test_rpcapi(self, method, *args, **kwargs):
        call_context = mock.MagicMock()
        with mock.patch.object(self.rpcapi.client, "prepare") as mock_prepare:
            mock_prepare.return_value = call_context
            with mock.patch.object(call_context, "call") as mock_call:
                method(*args, **kwargs)
                return mock_call

    def test_get_all_resource_mgr(self):
        type_ = "vcenter"
        mc = self._test_rpcapi(self.rpcapi.get_all_resource_mgrs,
                               *[self.context, type_])
        mc.assert_called_once_with(
            self.context, "get_all_resource_mgrs", type_=type_)

    def test_get_resource_mgr(self):
        id_ = "fake-id"
        mc = self._test_rpcapi(self.rpcapi.get_resource_mgr,
                               *[self.context, id_], with_inventory=True)
        mc.assert_called_once_with(
            self.context, "get_resource_mgr", id_=id_, with_inventory=True)

    def test_create_resource_mgr(self):
        data = {}
        mc = self._test_rpcapi(self.rpcapi.create_resource_mgr,
                               *[self.context, data])
        mc.assert_called_once_with(
            self.context, "create_resource_mgr", data=data)

    def test_update_resource_mgr(self):
        update_data = {}
        id_ = "fake-id"
        mc = self._test_rpcapi(self.rpcapi.update_resource_mgr,
                               *[self.context, id_, update_data])
        mc.assert_called_once_with(
            self.context, "update_resource_mgr",
            id_=id_, update_data=update_data)

    def test_delete_resource_mgr(self):
        id_ = "fake-id"
        mc = self._test_rpcapi(self.rpcapi.delete_resource_mgr,
                               *[self.context, id_])
        mc.assert_called_once_with(
            self.context, "delete_resource_mgr", id_=id_)

    def test_get_all_resources(self):
        filters = {"type": "esxcluster"}
        mc = self._test_rpcapi(self.rpcapi.get_all_resources,
                               *[self.context, filters])
        mc.assert_called_once_with(
            self.context, "get_all_resources", filters=filters)

    def test_get_resource(self):
        id_ = "fake-id"
        mc = self._test_rpcapi(self.rpcapi.get_resource,
                               *[self.context, id_], with_inventory=True)
        mc.assert_called_once_with(
            self.context, "get_resource", id_=id_, with_inventory=True)

    def test_create_resource(self):
        data = {}
        mc = self._test_rpcapi(self.rpcapi.create_resource,
                               *[self.context, data])
        mc.assert_called_once_with(
            self.context, "create_resource", data=data)

    def test_activate_resource(self):
        id_ = "fake-id"
        data = {}
        mc = self._test_rpcapi(self.rpcapi.activate_resource,
                               *[self.context, id_, data])
        mc.assert_called_once_with(
            self.context, "activate_resource", id_=id_, data=data)

    def test_deactivate_resource(self):
        id_ = "fake-id"
        data = {}
        mc = self._test_rpcapi(self.rpcapi.deactivate_resource,
                               *[self.context, id_, data])
        mc.assert_called_once_with(
            self.context, "deactivate_resource", id_=id_, data=data)

    def test_update_resource(self):
        update_data = {}
        id_ = "fake-id"
        mc = self._test_rpcapi(self.rpcapi.update_resource,
                               *[self.context, id_, update_data])
        mc.assert_called_once_with(
            self.context, "update_resource", id_=id_, update_data=update_data)

    def test_delete_resource(self):
        id_ = "fake-id"
        mc = self._test_rpcapi(self.rpcapi.delete_resource,
                               *[self.context, id_])
        mc.assert_called_once_with(
            self.context, "delete_resource", id_=id_)

    def test_update_property(self):
        id_ = "fake-id"
        rsrc_id = "fake-rsrc-id"
        prop_name = "cluster_moid"
        prop_val = "domain-c1"
        mc = self._test_rpcapi(self.rpcapi.update_property,
                               *[self.context, id_, rsrc_id, prop_name,
                                 prop_val])
        mc.assert_called_once_with(
            self.context, "update_property", id_=id_,
            rsrc_id=rsrc_id, property_name=prop_name, property_value=prop_val)

    def test_provision_resource(self):
        id_ = "fake-id"
        data = {}
        mc = self._test_rpcapi(self.rpcapi.provision_resource,
                               *[self.context, id_, data])
        mc.assert_called_once_with(self.context, "provision_resource",
                                   id_=id_, data=data)
