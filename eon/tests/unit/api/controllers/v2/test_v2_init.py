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
import pecan

from eon.api.controllers import v2

from eon.tests.unit import base_test
from eon.api.controllers import link


class TestV2(base_test.TestCase):

    def setUp(self):
        base_test.TestCase.setUp(self)
        self.v2_obj = v2.V2()

    def test_convert(self):
        with mock.patch.object(link.Link, "make_link") as mock_Link:
            mock_Link.return_value = link.Link()
            pecan.request = mock.MagicMock()
            pecan.request.host_url = "/v2/res/"
            converted_obj = v2.V2.convert()
            self.assertTrue(hasattr(converted_obj, "resource_mgrs"))
