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
#

import contextlib

from mock import patch
from pyVmomi import vim

from eon.common.exception import OVSvAppException
import eon.common.log as logging
from eon.deployer.network.ovsvapp.install.dvs_adapter import DVSAdapter
from eon.deployer import util
from eon.tests.unit import tests
from eon.tests.unit.deployer import fake_inputs

LOG = logging.getLogger('eon.deployer.network.ovsvapp.install.dvs_adapter')


class Pnic:
    device = 'pnic-1'


class DvPgSpec:

    class defaultPortConfig:

        class securityPolicy:
            allowPromiscuous = False
            forgedTransmits = False

        class vlan:
            inherited = False
            vlanId = None


class NicTeaming:
    policy = 'failover_explicit'
    notifySwitches = False
    failureCriteria = 5


class DVS:

    class FetchDVPorts:

        def __init__(self, fake_input):
            self.fake_input = fake_input

        class dv_port:

            class connectee:
                nicKey = '1'

            class config:
                name = ['port-1', 'port-2']

    name = 'DVS-1'

    class AddDVPortgroup_Task:

        def __init__(self, spec_list):
            self.spec_list = spec_list

    class config:

        class member:

            class config:
                host = 'fake-host1'

        host = [member]
        configVersion = '1.0'
        description = 'fake-description'

        class defaultPortConfig:
            uplinkTeamingPolicy = None
            vlan = vim.dvs.VmwareDistributedVirtualSwitch.VlanSpec()

    class ReconfigureDvs_Task:

        def __init__(self, spec):
            pass

    class ReconfigureDVPortgroup_Task:

        def __init__(self, spec):
            pass


# Change cloud_network_type, vlan, vlan_type etc. for different test cases
network = fake_inputs.data.get('portGroups')[1]


class NetworkFolder:

    class CreateDVS_Task:

        def __init__(self, spec):
            pass


class TestDvsAdapter(tests.BaseTestCase):

    def setUp(self):
        super(TestDvsAdapter, self).setUp()
        self.dvs_config = DVSAdapter()

    def test_get_used_pnics(self):
        output = self.dvs_config._get_used_pnics(
            {'config.network.vswitch': [],
             'config.network.proxySwitch': []})
        self.assertEqual([], output)

    def test_get_free_physical_nic(self):
        with contextlib.nested(
            patch.object(DVSAdapter, '_validate_host_pnic',
                         return_value=['pnic1']),
            patch.object(DVSAdapter, '_get_used_pnics',
                         return_value='pnic1')) as (
                mock_validate_host_pnic, mock_get_used_pnics):
            output = self.dvs_config._get_free_physical_nic('host',
                                                            'host_pnic')
            self.assertEqual(['pnic1'], output)
            self.assertTrue(mock_validate_host_pnic.called)
            self.assertTrue(mock_get_used_pnics.called)

    def test_validate_host_pnic(self):
        output = self.dvs_config._validate_host_pnic(
            {
                'config.network.pnic': [Pnic]
            },
            ['pnic-1'])
        self.assertEqual(['pnic-1'], output)

    def test_set_security_policy(self):
        self.dvs_config.dv_pg_spec = DvPgSpec
        self.dvs_config._set_security_policy(True, True)
        self.assertEqual(True, DvPgSpec.defaultPortConfig.
                         securityPolicy.allowPromiscuous.value)
        self.assertEqual(True, DvPgSpec.defaultPortConfig.
                         securityPolicy.forgedTransmits.value)

    def test_get_vlan_range(self):
        output = self.dvs_config._get_vlan_range(['1-20'])
        self.assertEqual(1, output[0].start)
        self.assertEqual(20, output[0].end)

    def test_set_trunk_vlan_spec(self):
        self.dvs_config.dv_pg_spec = DvPgSpec
        self.dvs_config._set_trunk_vlan_spec(['1-30'])
        self.assertTrue(1, DvPgSpec.defaultPortConfig.vlan.vlanId[0].start)
        self.assertTrue(30, DvPgSpec.defaultPortConfig.vlan.vlanId[0].end)

    def test_set_vlan_spec_not_vlan(self):
        with patch.object(DVSAdapter, '_set_vlan_id_spec') as(
                mock_set_vlan_id_spec):
            self.dvs_config._set_vlan_spec('', 'vlan')
            self.assertTrue(mock_set_vlan_id_spec.called)

    def test_set_vlan_spec_trunk(self):
        with contextlib.nested(
                patch.object(util, 'str2list'),
                patch.object(DVSAdapter, '_set_trunk_vlan_spec')) as (
                    mock_str2list, mock_set_trunk_vlan_spec):
            self.dvs_config._set_vlan_spec('30', 'trunk')
            self.assertTrue(mock_str2list.called)
            self.assertTrue(mock_set_trunk_vlan_spec.called)

    def test_set_vlan_spec_vlan(self):
        with contextlib.nested(
                patch.object(util, 'str2list'),
                patch.object(DVSAdapter, '_set_vlan_id_spec')) as (
                    mock_str2list, mock_set_vlan_id_spec):
            self.dvs_config._set_vlan_spec('30', 'vlan')
            self.assertTrue(mock_str2list.called)
            self.assertTrue(mock_set_vlan_id_spec.called)

    def test_set_vlan_spec_none(self):
        with contextlib.nested(
                patch.object(util, 'str2list'),
                patch.object(DVSAdapter, '_set_vlan_id_spec')) as (
                    mock_str2list, mock_set_vlan_id_spec):
            self.dvs_config._set_vlan_spec('30', 'none')
            self.assertTrue(mock_str2list.called)
            self.assertTrue(mock_set_vlan_id_spec.called)

    def test_fetch_uplink_dv_ports(self):
        output = self.dvs_config._fetch_uplink_dv_ports(DVS)
        self.assertEqual(True, output.fake_input.uplinkPort)

    def test_get_uplink_nic_map(self):
        with patch.object(DVSAdapter, '_fetch_uplink_dv_ports',
                          return_value=[DVS.FetchDVPorts.dv_port]) as (
                mock_uplink_dv_ports):
            output = self.dvs_config._get_uplink_nic_map(DVS)
            self.assertTrue('1' in output.keys())
            self.assertEqual(['port-1', 'port-2'], output['1'])
            self.assertTrue(mock_uplink_dv_ports.called)

    def test_get_num_dvs_nics(self):
        with patch.object(DVSAdapter, '_fetch_uplink_dv_ports',
                          return_value=[DVS.FetchDVPorts.dv_port]) as (
                mock_fetch_uplink_dv_ports):
            output = self.dvs_config._get_num_dvs_nics('data_dvs')
            self.assertEqual(1, output)
            self.assertTrue(mock_fetch_uplink_dv_ports.called)

    def test_set_uplink_port_order(self):
        with patch.object(DVSAdapter, '_get_uplink_nic_map',
                          return_value={'port-1': 'eth2'}) as (
                mock_get_uplink_nic_map):
            self.dvs_config._set_uplink_port_order(DVS, '')
            self.assertTrue(mock_get_uplink_nic_map.called)

    def test_set_notify_switches_config(self):
        self.dvs_config.nic_teaming = NicTeaming
        with patch.object(util, 'str2bool',
                          return_value=True) as mock_str2bool:
            self.dvs_config._set_notify_switches_config('True')
            self.assertEqual(True, NicTeaming.notifySwitches.value)
            self.assertTrue(mock_str2bool)

    def test_set_failover_detection_config(self):
        self.dvs_config.nic_teaming = NicTeaming
        self.dvs_config._set_failover_detection_config('2')
        self.assertEqual(True, NicTeaming.failureCriteria.checkBeacon.value)

    def test_set_loadbalancing_config(self):
        self.dvs_config.nic_teaming = NicTeaming
        self.dvs_config._set_loadbalancing_config('1')
        self.assertEqual('loadbalance_srcid', NicTeaming.policy.value)
        self.dvs_config._set_loadbalancing_config('2')
        self.assertEqual('loadbalance_ip', NicTeaming.policy.value)
        self.dvs_config._set_loadbalancing_config('3')
        self.assertEqual('loadbalance_srcmac', NicTeaming.policy.value)
        self.dvs_config._set_loadbalancing_config('4')
        self.assertEqual('loadbalance_loadbased', NicTeaming.policy.value)
        self.dvs_config._set_loadbalancing_config('5')
        self.assertEqual('failover_explicit', NicTeaming.policy.value)

    def test_set_nic_teaming_policy(self):
        with contextlib.nested(
                patch.object(DVSAdapter, '_set_notify_switches_config'),
                patch.object(DVSAdapter, '_set_failover_detection_config'),
                patch.object(DVSAdapter, '_set_loadbalancing_config'),
                patch.object(DVSAdapter, '_set_uplink_port_order')) as (
                    mock_get_notify_switches_config,
                    mock_get_failover_detection_config,
                    mock_get_loadbalancing_config,
                    mock_get_uplink_port_order):
            self.dvs_config._set_nic_teaming_policy(
                DVS, fake_inputs.data["portGroups"][0])
            self.assertTrue(mock_get_notify_switches_config.called)
            self.assertTrue(mock_get_failover_detection_config.called)
            self.assertTrue(mock_get_loadbalancing_config.called)
            self.assertTrue(mock_get_uplink_port_order.called)

    def test_add_dv_port_groups(self):
        with patch.object(util.VMwareUtils,
                          'wait_for_task') as mock_wait_for_task:
            self.dvs_config.add_dv_port_groups(fake_inputs.session,
                                               DVS, network)
            self.assertTrue(mock_wait_for_task.called)

    def test_create_host_config_spec(self):
        with patch.object(vim.HostSystem, '__init__', return_value=None) as (
                mock_constructor):
            self.vim_obj = vim.HostSystem()
            self.assertTrue(mock_constructor.called)

        with patch.object(DVSAdapter, '_get_free_physical_nic',
                          return_value=['pnic1', 'pnic2']) as (
                mock_get_free_physical_nic):
            self.dvs_config._create_host_config_spec([{'obj': self.vim_obj}],
                                                     'pnic_device')
            self.assertTrue(mock_get_free_physical_nic.called)

    def test_get_dvs_create_spec(self):
        output = self.dvs_config._get_dvs_create_spec('dvs_name', '1', 1700)
        self.assertEqual(1700, output[1].maxMtu)
        self.assertEqual('dvUplink0',
                         output[1].uplinkPortPolicy.uplinkPortName[0])

    def test_create_dvSwitch(self):
        with patch.object(vim.DistributedVirtualSwitch, '__init__',
                          return_value=None) as(
                mock_constructor):
            self.dvs_conf = vim.DistributedVirtualSwitch()
            self.assertTrue(mock_constructor.called)

        with contextlib.nested(
            patch.object(DVSAdapter, '_create_host_config_spec'),
            patch.object(util.VMwareUtils, 'wait_for_task',
                         return_value=self.dvs_conf)) as (
                mock_create_host_config_spec, mock_wait_for_task):
            self.dvs_config.create_dvSwitch(fake_inputs.session, NetworkFolder,
                                            'hosts', 'dvs_name',
                                            'pnic_device', 1500)
            self.assertTrue(mock_create_host_config_spec.called)
            self.assertTrue(mock_wait_for_task.called)

    def test_create_dvs_skeleton(self):
        with patch.object(vim.DistributedVirtualSwitch, '__init__',
                          return_value=None) as(
                mock_constructor):
            self.dvs_conf = vim.DistributedVirtualSwitch()
            self.assertTrue(mock_constructor.called)

        with patch.object(util.VMwareUtils, 'wait_for_task',
                          return_value=self.dvs_conf) as mock_wait_for_task:
            self.dvs_config.create_dvs_skeleton(fake_inputs.session,
                                                NetworkFolder, 'dvs_name',
                                                'pnic_device', 1500)
            self.assertTrue(mock_wait_for_task.called)

    def test_reconfigure_dvs(self):
        with contextlib.nested(
            patch.object(DVSAdapter, '_create_host_config_spec'),
            patch.object(util.VMwareUtils, 'wait_for_task')) as (
                mock_create_host_config_spec, mock_wait_for_task):
            self.dvs_config.reconfigure_dvs(fake_inputs.session, DVS,
                                            [{'obj': 'fake-host2'}],
                                            'pnic_device')
            self.assertTrue(mock_create_host_config_spec.called)
            self.assertTrue(mock_wait_for_task.called)

    def test_reconfigure_dv_portgroup_if_no_pnics(self):
        with contextlib.nested(
            patch.object(DVSAdapter, '_get_num_dvs_nics',
                         return_value=None),
            patch.object(util.VMwareUtils, 'wait_for_task'),
            patch.object(DVSAdapter, '_set_security_policy'),
            patch.object(DVSAdapter, '_set_nic_teaming_policy')) as (
                mock_get_num_dvs_nics, mock_wait_for_task,
                mock_get_security_policy, mock_set_nic_teaming_policy):
            self.dvs_config.reconfigure_dv_portgroup(fake_inputs.session, DVS,
                                                     'DVS', network)
            self.assertTrue(mock_get_num_dvs_nics.called)
            self.assertTrue(mock_wait_for_task.called)
            self.assertTrue(mock_get_security_policy.called)
            self.assertFalse(mock_set_nic_teaming_policy.called)

    def test_reconfigure_dv_portgroup_type_vlan(self):
        with contextlib.nested(
            patch.object(DVSAdapter, '_get_num_dvs_nics',
                         return_value=('pnic1', 'pnic2')),
            patch.object(util.VMwareUtils, 'wait_for_task'),
            patch.object(DVSAdapter, '_set_security_policy'),
            patch.object(DVSAdapter, '_set_nic_teaming_policy')) as (
                mock_get_num_dvs_nics, mock_wait_for_task,
                mock_get_security_policy, mock_set_nic_teaming_policy):
            self.dvs_config.reconfigure_dv_portgroup(fake_inputs.session, DVS,
                                                     'DVS', network)
            self.assertTrue(mock_get_num_dvs_nics.called)
            self.assertTrue(mock_wait_for_task.called)
            self.assertTrue(mock_get_security_policy.called)
            self.assertTrue(mock_set_nic_teaming_policy.called)

    def test_reconfigure_dv_portgroup_type_vxlan(self):
        network['cloud_network_type'] = 'vxlan'
        with contextlib.nested(
            patch.object(DVSAdapter, '_get_num_dvs_nics',
                         return_value=('pnic1', 'pnic2')),
            patch.object(util.VMwareUtils, 'wait_for_task'),
            patch.object(DVSAdapter, '_set_security_policy'),
            patch.object(DVSAdapter, '_set_nic_teaming_policy')) as (
                mock_get_num_dvs_nics, mock_wait_for_task,
                mock_get_security_policy, mock_set_nic_teaming_policy):
            self.dvs_config.reconfigure_dv_portgroup(fake_inputs.session, DVS,
                                                     'DVS', network)
            self.assertTrue(mock_get_num_dvs_nics.called)
            self.assertTrue(mock_wait_for_task.called)
            self.assertTrue(mock_get_security_policy.called)
            self.assertTrue(mock_set_nic_teaming_policy.called)

    def test_reconfigure_dv_portgroup_exception(self):
        with contextlib.nested(
            patch.object(DVSAdapter, '_get_num_dvs_nics',
                         return_value=None),
            patch.object(util.VMwareUtils, 'wait_for_task',
                         return_value=vim.fault.VimFault()),
            patch.object(DVSAdapter, '_set_security_policy'),
            patch.object(DVSAdapter, '_set_nic_teaming_policy'),
            patch.object(LOG, 'exception')) as (
                mock_get_num_dvs_nics, mock_wait_for_task,
                mock_get_security_policy, mock_set_nic_teaming_policy,
                mock_log):
            self.assertRaises(
                OVSvAppException,
                lambda: self.dvs_config.reconfigure_dv_portgroup(
                    fake_inputs.session, DVS, 'DVS', network))
            self.assertTrue(mock_get_num_dvs_nics.called)
            self.assertTrue(mock_wait_for_task.called)
            self.assertTrue(mock_get_security_policy.called)
            self.assertFalse(mock_set_nic_teaming_policy.called)
            self.assertTrue(mock_log.called)
