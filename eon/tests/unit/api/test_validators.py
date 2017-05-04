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

import uuid

from eon import validators
from eon.common import exception
from eon.tests.unit.base_test import TestCase


class TestValidators(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.res_mang_val = validators.ResourceManagerValidator()
        self.res_val = validators.ResourceValidator()

    def test_assert_is_valid_uuid_from_uri_invalid(self):
        _uuid = "123"
        self.assertRaises(exception.InvalidUUIDInURI,
            validators.assert_is_valid_uuid_from_uri,
            _uuid)

    def test_assert_is_valid_uuid_from_uri(self):
        _uuid = str(uuid.uuid4())
        self.assertIsNone(
            validators.assert_is_valid_uuid_from_uri(_uuid))

    def test_validate_get_true(self):
        kws = {"type": "vcenter"}
        self.assertEqual(None, self.res_mang_val.validate_get(kws))

    def test_validate_get_Invalid_key(self):
        kws = {"typed": "vcenter"}
        self.assertRaises(exception.Invalid,
                          self.res_mang_val.validate_get,
                          kws)

    def test_validate_get_invalid_type(self):
        kws = {"type": "vcenter1"}
        self.assertRaises(exception.Invalid,
                          self.res_mang_val.validate_get,
                          kws)
