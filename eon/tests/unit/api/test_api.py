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

from eon import api
from eon.tests.unit import base_test
import webob


class TestAPI(base_test.TestCase):

    def test_load_query_params(self):
        kw = {}
        validator_out = {"type": None, "state": None}
        validator = mock.Mock
        self.assertEqual(validator_out,
                         api.load_query_params(kw, validator))

    def test_load_query_params_kws_type(self):
        kw = {"type": "vcenter"}
        validator_out = {"type": "vcenter", "state": None}
        validator = mock.Mock
        self.assertEqual(validator_out,
                         api.load_query_params(kw, validator))

    def test_load_query_params_kws_state(self):
        kw = {"state": "imported"}
        validator_out = {"type": None, "state": "imported"}
        validator = mock.Mock
        self.assertEqual(validator_out,
                         api.load_query_params(kw, validator))

    def test_load_query_params_kws_state_type(self):
        kw = {"state": "imported", "type": "esxcluster"}
        validator_out = kw
        validator = mock.Mock
        self.assertEqual(validator_out,
                         api.load_query_params(kw, validator))

    def test_load_body(self):
        req = self.req
        validator = mock.Mock
        self.assertEqual(json.loads(req.body),
                         api.load_body(req, validator))

    def test_load_body_json_error_1(self):
        req = self.req
        validator = mock.Mock
        req.body = {"asd": "asd"}
        self.assertRaises(webob.exc.HTTPBadRequest,
                         api.load_body,
                         req, validator)

    def test_load_body_json_error_2(self):
        req = self.req
        validator = mock.Mock
        req.body = '{"asd"}'
        self.assertRaises(webob.exc.HTTPBadRequest,
                         api.load_body,
                         req, validator)
