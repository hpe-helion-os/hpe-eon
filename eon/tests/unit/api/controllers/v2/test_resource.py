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

import json
import mock

from eon.api.controllers.v2 import resources
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
import webob


class TestResources(base_test.TestCase):

    def setUp(self):
        base_test.TestCase.setUp(self)
        self.rsrc = resources.Resources()
        resources.pecan = mock.MagicMock()
        resources.pecan.request = mock.MagicMock()
        self.req = resources.pecan.request
        self.req.context = mock.MagicMock()
        self.context = self.req.context

    def test_get_all(self):
        filters = {}
        filters_called_with = {"type": None, "state": None}
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resources') as get_all_m:
            self.rsrc.get_all(**filters)
            get_all_m.assert_called_once_with(self.context,
                                              filters_called_with)

    def test_get_all_with_filter_type(self):
        filters = {"type": "esxcluster"}
        filters_called_with = {"type": "esxcluster", "state": None}
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resources') as get_all_m:
            self.rsrc.get_all(**filters)
            get_all_m.assert_called_once_with(self.context,
                                              filters_called_with)

    def test_get_all_with_filter_state(self):
        filters = {"state": "imported"}
        filters_called_with = {"type": None, "state": "imported"}
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resources') as get_all_m:
            self.rsrc.get_all(**filters)
            get_all_m.assert_called_once_with(self.context,
                                              filters_called_with)

    def test_get_all_with_filter_state_type(self):
        filters = {"type": "esxcluster", "state": "imported"}
        filters_called_with = filters
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resources') as get_all_m:
            self.rsrc.get_all(**filters)
            get_all_m.assert_called_once_with(self.context,
                                              filters_called_with)

    def test_get_with_wrong_filter(self):
        filters = {"type": "cluster"}
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_all_resources'):
            self.assertRaises(webob.exc.HTTPBadRequest,
                              self.rsrc.get_all, **filters)

    def test_delete(self):
        res_id = fake_data.fake_id1
        with mock.patch.object(self.req.rpcapi_v2,
                               'delete_resource') as delete_m:
            self.rsrc.delete(res_id)
            delete_m.assert_called_once_with(self.context, res_id)

    def test_get(self):
        res_id = fake_data.fake_id1
        with mock.patch.object(self.req.rpcapi_v2,
                               'get_resource') as delete_m:
            self.rsrc.get(res_id)
            delete_m.assert_called_once_with(self.context, res_id)

    def test_post_baremetal(self):
        with mock.patch.object(self.req.rpcapi_v2,
                               'create_resource') as create_r:
            self.req.body = json.dumps(fake_data.baremetal_create_data)
            self.rsrc.post()
            create_r.assert_called_once_with(self.context,
                                             fake_data.baremetal_create_data)

    def test_post_kvm(self):
        with mock.patch.object(self.req.rpcapi_v2,
                               'create_resource') as create_r:
            self.req.body = json.dumps(fake_data.kvm_create_data)
            self.rsrc.post()
            create_r.assert_called_once_with(self.context,
                                             fake_data.kvm_create_data)

    def test_post_baremetal_failure(self):
            self.req.body = json.dumps(fake_data.baremetal_create_data_fail)
            self.assertRaises(webob.exc.HTTPBadRequest, self.rsrc.post)

    def test_post_kvm_failure(self):
            self.req.body = json.dumps(fake_data.kvm_create_data_fail)
            self.assertRaises(webob.exc.HTTPBadRequest, self.rsrc.post)
