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

from eon.common import exception
from eon.virt.baremetal import driver
from eon.tests.unit import base_test
from eon.tests.unit import fake_data


class Prop(object):
    """Property Object base class."""

    def __init__(self):
        self.name = None
        self.value = None


class TestDriver(base_test.TestCase):

    def setUp(self):
        super(TestDriver, self).setUp()
        self.bm_driver = driver.BaremetalDriver()
        driver.eon.db = mock.MagicMock()

    @mock.patch('eon.common.utils.run_command_get_output')
    def test_validate_create(self, mock_exc):
        context = {}
        create_data = fake_data.baremetal_create_data
        cmd = (' ' .join("ipmitool -I lanplus -U %s -P %s -H %s power status"
                         % (create_data['ilo_user'],
                            create_data['ilo_password'],
                            create_data['ilo_ip']
                            )
                         )
               )
        data = self.bm_driver.validate_create(context, create_data)
        self.assertEquals(create_data, data, "Invalid values returned")
        mock_exc.called_once_with(cmd)

    @mock.patch('eon.common.utils.run_command_get_output')
    def test_validate_create_excep1(self, mock_exc):
        mock_exc.return_value = "Error: failed"
        context = {}
        create_data = fake_data.baremetal_create_data
        cmd = (' ' .join("ipmitool -I lanplus -U %s -P %s -H %s power status"
                         % (create_data['ilo_user'],
                            create_data['ilo_password'],
                            create_data['ilo_ip']
                            )
                         )
               )
        self.assertRaises(exception.CreateException,
                          self.bm_driver.validate_create,
                          context, create_data)
        mock_exc.called_once_with(cmd)

    def test_validate_delete(self):
        fake_data.res_mgr_data1["state"] = "imported"
        self.assertIsNone(self.bm_driver.validate_delete(
            fake_data.res_mgr_data1))

    def test_validate_delete_exception(self):
        fake_data.res_mgr_data1["state"] = "importing"
        self.assertRaises(exception.EonException,
                          self.bm_driver.validate_delete,
                          fake_data.res_mgr_data1)

    def test_get_properties(self):
        vals = self.bm_driver.get_properties(fake_data.res_data)
        self.assertEqual(vals['mac_addr'], "ma:ya:nk",
                         "Invalid value returned")

    def test_validate_update(self):
        db_api = self.bm_driver.db_api
        with mock.patch.object(db_api, "update_property") as db_api:
            self.bm_driver.validate_update(
                self.context, fake_data.res_mgr_data1, fake_data.update_data)
