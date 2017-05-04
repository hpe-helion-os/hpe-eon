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


from eon.deployer.network.noop.installer import NoOpInstaller
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


class TestNoOpInstaller(tests.BaseTestCase):

    def setUp(self):
        super(TestNoOpInstaller, self).setUp()
        self.noOp_installer = NoOpInstaller()

    def test_setup_network(self):
        pass

    def test_create(self):
        data = fake_inputs.data
        expected = {data.get("vcenter_configuration").get("cluster"): None}
        self.assertEqual(self.noOp_installer.create(data), expected)

    def test_update(self):
        pass

    def test_delete(self):
        pass

    def test_teardown_network(self):
        pass

    def test_get_info(self):
        pass
