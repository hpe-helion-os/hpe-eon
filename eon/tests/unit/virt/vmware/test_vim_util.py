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

from oslo_vmware import vim_util as vmware_util

from eon.virt.vmware import vim_util
from testtools import TestCase


class TestVIMUtil(TestCase):

    def setUp(self):
        super(TestVIMUtil, self).setUp()

    def test_create_data_object(self):
        client_factory = mock.MagicMock()
        spec_name = 'spec_name'
        self.assertTrue(vim_util.create_data_object(client_factory,
                                                    spec_name))

    def test_get_objects(self):
        with mock.patch.object(vmware_util, "get_objects") \
                        as get_objs:
            get_objs.return_value = []
            self.assertEqual([],
                             vim_util.get_objects('vim',
                                                  'type_',
                                                  'properties_to_collect'))

    def test_create_filter(self):
        vim = mock.MagicMock()
        with contextlib.nested(
            mock.patch.object(vmware_util, "build_recursive_traversal_spec"),
            mock.patch.object(vmware_util, "build_object_spec"),
            mock.patch.object(vmware_util, "build_property_spec"),
            mock.patch.object(vmware_util, "build_property_filter_spec"),
            ):
            self.assertIsNone(vim_util.create_filter(vim))

    def test_wait_for_updates_ex(self):
        vim = mock.MagicMock()
        self.assertTrue(vim_util.wait_for_updates_ex(vim,
                                                'version'))

    def test_retreive_vcenter_inventory(self):
        vim = mock.MagicMock()
        self.assertTrue(vim_util.retreive_vcenter_inventory(vim))
