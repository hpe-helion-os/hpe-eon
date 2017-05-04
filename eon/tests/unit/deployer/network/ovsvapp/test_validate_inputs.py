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

from mock import patch

from eon.common import exception
from eon.deployer import util
from eon.deployer.network.ovsvapp.util.validate_inputs import ValidateInputs
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs


class TestValidateInputs(tests.BaseTestCase):

    def setUp(self):
        super(TestValidateInputs, self).setUp()
        self.validate_inputs = ValidateInputs(fake_inputs.data)

    def test_raise_validation_error(self):
        pass

    def test_validate_CIDR(self):
        self.assertTrue(self.validate_inputs.validate_CIDR('10.10.10.0/24'))
        self.assertTrue(self.validate_inputs.validate_CIDR('10.10.10.0/18'))

    def test_validate_nic_teaming_inputs(self):
        nic_teaming = {'load_balancing': 1,
                       'network_failover_detection': 1}
        self.validate_inputs._validate_nic_teaming_inputs(nic_teaming,
                                                          'net_name')

    def test_validate_vlan_inputs(self):
        self.validate_inputs._validate_vlan_inputs('1,3,4-30', 'network_name')

    def test_validate_vlan_type(self):
        pass

    def test_compare_lists(self):
        list1 = [1, 2]
        list2 = [1, 2]
        list3 = [3, 4]
        self.assertTrue(self.validate_inputs._compare_lists(list1, list2))
        self.assertFalse(self.validate_inputs._compare_lists(list1, list3))

    def test_validate_network_inputs(self):
        dvs_names = ['MGMT-DVS', 'TRUNK-DVS']
        with contextlib.nested(
            patch.object(ValidateInputs, '_validate_vlan_inputs'),
            patch.object(ValidateInputs, '_validate_vlan_type'),
            patch.object(ValidateInputs,
                         '_validate_nic_teaming_inputs')) as (
                mock_validate_vlan_inputs, mock_validate_vlan_type,
                mock_validate_nic_teaming_inputs):
            output = self.validate_inputs.validate_network_inputs(dvs_names)
            self.assertEqual(['MGMT-DVS', 'MGMT-DVS', 'TRUNK-DVS'],
                             output)
            self.assertTrue(mock_validate_vlan_inputs.called)
            self.assertTrue(mock_validate_vlan_type.called)
            self.assertTrue(mock_validate_nic_teaming_inputs.called)

    def test_validate_network_inputs_invalid_vm_config(self):
        dvs_names = ['MGMT-DVS', 'TRUNK-DVS']
        with contextlib.nested(
            patch.object(ValidateInputs, '_validate_vlan_inputs'),
            patch.object(ValidateInputs, '_validate_vlan_type'),
            patch.object(ValidateInputs,
                         '_validate_nic_teaming_inputs'),
            patch.object(util, 'get_vmconfig_input', return_value=None),
            patch.object(util, 'get_conf_pg')) as (
                mock_validate_vlan_inputs, mock_validate_vlan_type,
                mock_validate_nic_teaming_inputs, mock_get_vmconfig_input,
                mock_get_conf_pg):
            self.assertRaises(
                exception.OVSvAppValidationError,
                lambda: self.validate_inputs.validate_network_inputs(
                    dvs_names))
            self.assertTrue(mock_validate_vlan_inputs.called)
            self.assertTrue(mock_validate_vlan_type.called)
            self.assertTrue(mock_validate_nic_teaming_inputs.called)
            self.assertTrue(mock_get_vmconfig_input.called)
            self.assertFalse(mock_get_conf_pg.called)

    def test_validate_network_inputs_invalid_portgroup_name(self):
        dvs_names = ['MGMT-DVS', 'TRUNK-DVS']
        with contextlib.nested(
            patch.object(ValidateInputs, '_validate_vlan_inputs'),
            patch.object(ValidateInputs, '_validate_vlan_type'),
            patch.object(ValidateInputs,
                         '_validate_nic_teaming_inputs'),
            patch.object(util, 'get_conf_pg', return_value=None)) as (
                mock_validate_vlan_inputs, mock_validate_vlan_type,
                mock_validate_nic_teaming_inputs, mock_get_conf_pg):
            self.assertRaises(
                exception.OVSvAppValidationError,
                lambda: self.validate_inputs.validate_network_inputs(
                    dvs_names))
            self.assertTrue(mock_validate_vlan_inputs.called)
            self.assertTrue(mock_validate_vlan_type.called)
            self.assertTrue(mock_validate_nic_teaming_inputs.called)
            self.assertTrue(mock_get_conf_pg.called)

    def test_validate_dvs_inputs(self):
        self.assertEqual(['MGMT-DVS', 'TRUNK-DVS'],
                         self.validate_inputs.validate_dvs_inputs())

    def test_validate_ip_inputs(self):
        with patch.object(ValidateInputs, 'validate_CIDR') as (
                mock_validate_CIDR):
            self.validate_inputs.validate_ip_inputs()
            self.assertTrue(mock_validate_CIDR.called)

    def test_validate_vnics(self):
        pass

    def test_validate_vmconfig_inputs(self):
        with patch.object(ValidateInputs, '_validate_vnics') as(
                mock_validate_vnics):
            self.validate_inputs.validate_vmconfig_inputs()
            self.assertTrue(mock_validate_vnics.called)

    def test_validate_inputs(self):
        with contextlib.nested(
            patch.object(ValidateInputs, 'validate_dvs_inputs'),
            patch.object(ValidateInputs, 'validate_network_inputs')) as(
                mock_validate_dvs_inputs,
                mock_validate_network_inputs):
            self.validate_inputs.validate_inputs(True)
            self.assertTrue(mock_validate_dvs_inputs.called)
            self.assertTrue(mock_validate_network_inputs.called)
