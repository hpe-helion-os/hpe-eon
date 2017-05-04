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
import json

from eon.api.controllers.v2 import resource_manager
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
import webob


class TestResources(base_test.TestCase):

    def setUp(self):
        base_test.TestCase.setUp(self)
        self.rsrc_mgrs = resource_manager.ResourceManager()
        resource_manager.pecan = mock.MagicMock()
        resource_manager.pecan.request = mock.MagicMock()
        self.req = resource_manager.pecan.request
        self.req.context = mock.MagicMock()
        self.context = self.req.context

    def test_get_all(self):
        filters = {}
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resource_mgrs') as get_all_m:
            self.rsrc_mgrs.get_all(**filters)
            get_all_m.assert_called_once_with(self.context, None)

    def test_get_all_with_filter_type(self):
        filters = {"type": "vcenter"}
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resource_mgrs') as get_all_m:
            self.rsrc_mgrs.get_all(**filters)
            get_all_m.assert_called_once_with(self.context, filters["type"])

    def test_get_with_wrong_filter(self):
        filters = {"type": "vcenter1"}
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resource_mgrs'):
            self.assertRaises(webob.exc.HTTPBadRequest,
                              self.rsrc_mgrs.get_all, **filters)

    def test_post(self):
        with mock.patch.object(self.req.rpcapi_v2,
                               'create_resource_mgr') as create_m:
            self.req.body = json.dumps(fake_data.create_data)
            self.rsrc_mgrs.post()
            create_m.assert_called_once_with(self.context,
                                             fake_data.create_data)

    def test_post_failure_1(self):
        expected_regexp = "Required parameters are not passed"
        with mock.patch.object(self.req.rpcapi_v2,
                               'create_resource_mgr'):
            self.req.body = json.dumps(fake_data.insufficient_create_data)
            self.assertRaisesRegexp(webob.exc.HTTPBadRequest, expected_regexp,
                                    self.rsrc_mgrs.post)

    def test_post_failure_2(self):
        expected_regexp = "Cannot be empty"
        with mock.patch.object(self.req.rpcapi_v2,
                               'create_resource_mgr'):
            self.req.body = json.dumps(fake_data.invalid_create_data)
            self.assertRaisesRegexp(webob.exc.HTTPBadRequest, expected_regexp,
                                    self.rsrc_mgrs.post)

    def test_delete(self):
        res_mgr_id = fake_data.fake_id1
        with mock.patch.object(self.req.rpcapi_v2,
                               'delete_resource_mgr') as delete_m:
            self.rsrc_mgrs.delete(res_mgr_id)
            delete_m.assert_called_once_with(self.context, res_mgr_id)

    def test_get(self):
        res_mgr_id = fake_data.fake_id1
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_resource_mgr') as delete_m:
            self.rsrc_mgrs.get(res_mgr_id)
            delete_m.assert_called_once_with(self.context, res_mgr_id)
