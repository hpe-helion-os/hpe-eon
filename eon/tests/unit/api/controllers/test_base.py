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
from webob import exc

from eon.api.controllers import base
from eon.tests.unit import base_test


class TestVersion(base_test.TestCase):

    @mock.patch('eon.api.controllers.base.Version.parse_headers')
    def test_init(self, mock_parse):
        a = mock.Mock()
        b = mock.Mock()
        mock_parse.return_value = (a, b)
        v = base.Version('test', 'foo', 'bar')

        mock_parse.assert_called_with('test', 'foo', 'bar')
        self.assertEqual(a, v.major)
        self.assertEqual(b, v.minor)

    def test_parse_headers(self):
        version = base.Version.parse_headers(
            {base.Version.string: '123.456'}, mock.ANY, mock.ANY)
        self.assertEqual((123, 456), version)

    def test_parse_headers_bad_length(self):
        self.assertRaises(
            exc.HTTPNotAcceptable,
            base.Version.parse_headers,
            {base.Version.string: '1'},
            "",
            "")
        self.assertRaises(
            exc.HTTPNotAcceptable, base.Version.parse_headers,
            {base.Version.string: '1.2.3'}, "", "")


class TestAPIBase(base_test.TestCase):
    def setUp(self):
        base_test.TestCase.setUp(self)
        self.api_base = base.APIBase()

    def test_unset_fields_except(self):
        except_list = []
        with mock.patch.object(self.api_base, "as_dict") as dict_m:
            dict_m.return_value = {"a": 1}
            self.api_base.unset_fields_except(except_list)
            dict_m.assert_called_once_with()
