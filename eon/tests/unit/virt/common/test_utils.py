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

import copy
import mock
import requests
import subprocess
import time
from mock import MagicMock
import contextlib
from eon.openstack.common import context as context_
from eon.virt.common import utils
from eon.virt.common.utils import VirtCommonUtils
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
from eon.virt import constants as virt_const
from eon.hlm_facade import hlm_facade_handler
from eon.common import exception
from eon.virt import constants
from oslo_config import cfg

CONF = cfg.CONF
JSON_DATA = {'cs-mgmt-controller': {'keystone-username': 'user',
                                    'keystone-password': 'password',
                                    'keystone-tenantname': "tenant"},
             'vip': "10.10.10.10"}

AUTH_DICT = {'os_username':
             JSON_DATA['cs-mgmt-controller']['keystone-username'],
             'os_password':
             JSON_DATA['cs-mgmt-controller']['keystone-password'],
             'os_tenant_name':
             JSON_DATA['cs-mgmt-controller']['keystone-tenantname'],
             'os_auth_url': "http://%s:5000/v2.0/" % JSON_DATA["vip"]
            }


class TestVirtCommonUtils(base_test.TestCase):

    def setUp(self):
        super(TestVirtCommonUtils, self).setUp()
        self.virt_utils = VirtCommonUtils()
        self.mock_obj = mock.Mock()
        self.db_api = mock.MagicMock()

    def test_create_servers_payload(self):
        fake_pl = fake_data.baremetal_resource_data
        pl = self.virt_utils.create_servers_payload(fake_pl, fake_pl)
        self.assertEquals(fake_pl['id'], pl['id'],
                          "Inconsistent name to id conversion")

    def test_create_servers_payload_extra_props(self):
        fake_pl = fake_data.rhel_resource_data
        copy_fake_pl = copy.deepcopy(fake_pl)
        pl = self.virt_utils.create_servers_payload(fake_pl, fake_pl)
        self.assertEquals(fake_pl['id'], pl['id'],
                          "Inconsistent name to id conversion")
        distro_id = virt_const.COBBLER_PROFILE_MAP[
                        copy_fake_pl['os_version']] + "-multipath"
        self.assertEquals(distro_id,
                          pl[virt_const.COBBLER_PROFILE],
                          "os-verison didn't match ")
        self.assertEquals(
            copy_fake_pl[virt_const.BOOT_FROM_SAN],
            pl[virt_const.HLM_PAYLOAD_MAP[virt_const.BOOT_FROM_SAN]],
                          "boot_from-san prop not added ")
        raw_properties = fake_pl.get('property')
        if raw_properties:
            for datum in raw_properties:
                key, value = datum.split('=', 1)
                fake_pl[key] = value
        self.assertEquals(fake_pl['new-random-prop'], pl['new-random-prop'],
                          "os-verison didn't match ")
        self.assertEquals(fake_pl['custom1'], pl['custom1'],
                          "os-verison didn't match ")
        self.assertEquals(fake_pl['hostname'], pl['hostname'],
                          "hostname didnot match")
        self.assertEquals(fake_pl['fcoe_interfaces'], pl['fcoe-interfaces'],
                          "fcoe-interfaces didnot match")

    @mock.patch('subprocess.Popen')
    def test_modify_servers_payload(self, mockPopen):
        fake_pl = fake_data.baremetal_resource_data
        popen_mock = mock.Mock(stdout=["#encrypted_password#\n"])
        mockPopen.return_value = popen_mock
        pl = self.virt_utils.create_servers_payload(fake_pl, fake_pl)
        newpl = self.virt_utils.modify_servers_payload(
            pl, fake_pl, virt_const.EON_RESOURCE_TYPE_HYPERV)
        self.assertEquals(fake_pl['id'], newpl['id'],
                          "Inconsistent name to id conversion")
        expected_val = "ansible_ssh_user=user" \
                       " ansible_ssh_pass=\"{{ lookup('pipe'," \
                       " '/usr/bin/eon-encrypt -d #encrypted_password# ')" \
                       " }}\" ansible_ssh_port=5986" \
                       " ansible_connection=winrm" \
                       " ansible_winrm_server_cert_validation=ignore"
        mockPopen.assert_called_once_with(['/usr/bin/eon-encrypt', 'password',
                                           '-k', ''],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
        self.assertEquals(newpl['ansible-options'], expected_val)
        self.assertTrue("nic-mapping" not in newpl)

    @mock.patch('subprocess.Popen')
    def test_modify_servers_payload_no_nic_mapping_key(self, mockPopen):
        fake_pl = fake_data.baremetal_resource_data
        popen_mock = mock.Mock(stdout=["#encrypted_password#\n"])
        mockPopen.return_value = popen_mock
        fake_pl.pop(virt_const.NIC_MAPPINGS)
        pl = self.virt_utils.create_servers_payload(fake_pl, fake_pl)
        newpl = self.virt_utils.modify_servers_payload(
            pl, fake_pl, virt_const.EON_RESOURCE_TYPE_HYPERV)
        self.assertEquals(fake_pl['id'], newpl['id'],
                          "Inconsistent name to id conversion")
        expected_val = "ansible_ssh_user=user" \
                       " ansible_ssh_pass=\"{{ lookup('pipe'," \
                       " '/usr/bin/eon-encrypt -d #encrypted_password# ')" \
                       " }}\" ansible_ssh_port=5986" \
                       " ansible_connection=winrm" \
                       " ansible_winrm_server_cert_validation=ignore"
        mockPopen.assert_called_once_with(['/usr/bin/eon-encrypt', 'password',
                                           '-k', ''],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
        self.assertEquals(newpl['ansible-options'], expected_val)
        self.assertTrue("nic-mapping" not in newpl)

    def _fake_nova_header(self):
        return {'User-Agent': "eon-deployer",
                'X-Auth-Token': "xyz",
                'accept': 'application/json',
                }

    def _fake_neutron_header(self):
        return {'User-Agent': "eon-deployer",
                'X-Auth-Token': "xyz",
                'accept': 'application/json',
                }

    def _fake_json_response(self):
        return {
            "hypervisors": [{
                "id": 2,
                "hypervisor_hostname": "domain-2.cluster-2"},
                {"id": 1,
                 "hypervisor_hostname": "domain-1.cluster-1",
                 "running_vms": 1}],
            "password": "password",
            "id": 1,
            "agents": [{"host": "proxy_name.hpiscmgmt.local",
                        "agent_type": "HP ISC L2 Agent",
                        "alive": True}]}

    def _fake_json_response_2(self):
        return {
            "hypervisors": [{
                "id": 2,
                "hypervisor_hostname": "domain-2.cluster-2"},
                {"id": 1,
                 "hypervisor_hostname": "hypervisor_hostname",
                 "running_vms": 1}],
            "password": "password",
            "id": 1,
            "agents": [{"host": "proxy_name.hpiscmgmt.local",
                        "agent_type": "HP ISC L2 Agent",
                        "alive": True}]}

    def _fake_json_response_3(self):
        return {
            "hypervisors": [{
                "id": 2,
                "hypervisor_hostname": "domain-2.cluster-2"},
                {"id": 1,
                 "hypervisor_hostname": "HYPERVISOR_hostname",
                 "running_vms": 1}],
            "password": "password",
            "id": 1,
            "agents": [{"host": "proxy_name.hpiscmgmt.local",
                        "agent_type": "HP ISC L2 Agent",
                        "alive": True}]}

    def _fake_json_response_4(self):
        return {
            "hypervisors": [{
                "id": 2,
                "hypervisor_hostname": "domain-2.cluster-2"},
                {"id": 1,
                 "hypervisor_hostname": "HYPERVISOR_HOSTNAME",
                 "running_vms": 0}],
            "password": "password",
            "id": 1,
            "agents": [{"host": "proxy_name.hpiscmgmt.local",
                        "agent_type": "HP ISC L2 Agent",
                        "alive": True}]}

    def _fake_json_response_5(self):
        return {
            "hypervisors": [{
                "id": 2,
                "hypervisor_hostname": "domain-0.cluster-0"},
                {"id": 1,
                 "hypervisor_hostname": "hypervisor_hostname",
                 "running_vms": 1}],
            "password": "password",
            "id": 1,
            "agents": [{"host": "proxy_name.hpiscmgmt.local",
                        "agent_type": "HP ISC L2 Agent",
                        "alive": True}]}

    def _fake_json_response_6(self):
        return {
            "hypervisors": [{
                "id": 2,
                "hypervisor_hostname": "domain-2.cluster-2"},
                {"id": 1,
                 "hypervisor_hostname": "hypervisor_hostname",
                 "running_vms": 1}],
            "password": "password",
            "id": 1,
            "agents": [
                        {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "host": "ovsvapp-10-1-214-177",
                         "agent_type": "HP VCN L2 Agent",
                         "configurations": {"esx_host_name": "10.1.214.177"}
                         },
                       {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "host": "ovsvapp-10-1-214-178",
                         "agent_type": "HP VCN L2 Agent",
                         "configurations": {"esx_host_name": "10.1.214.178"}
                         },

                        ]}

    def _fake_json_response_7(self):
        return {
            "hypervisors": [{
                "id": 2,
                "service": {},
                "hypervisor_hostname": "domain-0.cluster-0"},
                {"id": 1,
                 "service": {},
                 "hypervisor_hostname": "hypervisor_hostname",
                 "running_vms": 1},
                {"service": {"host": "hypervisor_hostname", "id": 2}}],
            "password": "password",
            "id": 1,
            "agents": [
                        {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "host": "ovsvapp-10-1-214-177",
                         "agent_type": "HP VCN L2 Agent",
                         "configurations": {"esx_host_name": "10.1.214.177"}
                         },
                       {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "host": "ovsvapp-10-1-214-178",
                         "agent_type": "HP VCN L2 Agent",
                         "configurations": {"esx_host_name": "10.1.214.178"}
                         },
                        ],
            "status_code": 202}

    def _fake_json_response_8(self):
        return {
            "hypervisors": [{
                "id": 2,
                "service": {},
                "hypervisor_hostname": "domain-0.cluster-0"},
                {"id": 1,
                 "service": {},
                 "hypervisor_hostname": "hypervisor_hostname",
                 "running_vms": 1},
                {"service": {"host": "hypervisor_hostname", "id": 2}}],
            "password": "password",
            "id": 1,
            "agents": [
                        {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "id": u"1234",
                         "host": "hypervisor_hostname",
                         "agent_type": "HP VCN L2 Agent",
                         "configurations": {"esx_host_name": u"10.1.214.177"}
                         },
                       {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "id": u"5678",
                         "host": "ovsvapp-10-1-214-178",
                         "agent_type": "HP VCN L2 Agent",
                         "configurations": {"esx_host_name": u"10.1.214.178"}
                         },
                        ],
            "status_code": 202}

    def _fake_keystonrc(self):
        return {'os_auth_url': 'http://10.10.10.10:5000/v2.0/',
                'os_password': 'password',
                'os_tenant_name': 'tenant',
                'os_username': 'user'}

    def _fake_neutron_agents_empty(self):
        return {
            "agents": []
        }

    def _fake_neutron_agents(self):
        return {
            "agents": [
                {
                    "agent_type": virt_const.NEUTRON_AGENT_TYPE.get('kvm'),
                    "alive": True,
                    "host": "hyperv-host-1",
                },
            ]}

    def test_get_nova_hypervisor_info_activation_success(self):
            fake_response = self.mock_obj
            fake_response.json = self._fake_json_response
            with mock.patch.object(requests, "get") as req_m:
                req_m.return_value = fake_response
                ret = utils.get_nova_hypervisor_info(
                    "url", "headers", "domain-2.cluster-2",
                     action="activation")
                self.assertEqual(2, ret)

    def test_get_nova_hypervisor_info_activation_failure(self):
        fake_response = self.mock_obj
        fake_response.json = self._fake_json_response
        with mock.patch.object(requests, "get") as req_m:
            req_m.return_value = fake_response
            req_m.side_effect = requests.exceptions.ConnectionError
            with mock.patch.object(time, "sleep"):
                ret = utils.get_nova_hypervisor_info(
                    "url",
                    "headers",
                    "domain-0.cluster-0",
                    action="activation")
                self.assertEqual(None, ret)

    def test_get_nova_hypervisor_info_deactivation_success(self):
        fake_response = self.mock_obj
        fake_response.json = self._fake_json_response_5
        with mock.patch.object(requests, "get") as req_m:
            req_m.return_value = fake_response
            with mock.patch.object(time, "sleep"):
                ret = utils.get_nova_hypervisor_info(
                    "url",
                    "headers",
                    "domain-0.cluster-1",
                    action="deactivation")
                self.assertTrue(ret)

    def test_get_nova_hypervisor_info_deactivation_failure(self):
        fake_response = self.mock_obj
        fake_response.json = self._fake_json_response_5
        with mock.patch.object(requests, "get") as req_m:
            req_m.return_value = fake_response
            with mock.patch.object(time, "sleep"):
                ret = utils.get_nova_hypervisor_info(
                    "url",
                    "headers",
                    "domain-0.cluster-0",
                    action="deactivation")
                self.assertEqual(None, ret)

    def test_check_neutron_agent_list_failure(self):
        resp = MagicMock()
        fake_agents = self._fake_neutron_agents()
        fake_agents["agents"][0]["alive"] = True
        resp.json.return_value = fake_agents
        with mock.patch.object(utils.requests, "get") as req_get:
            req_get.return_value = resp
            req_get.side_effect = requests.exceptions.ConnectionError
            host_name = fake_agents["agents"][0]["host"]
            agent_type = fake_agents["agents"][0]["agent_type"]
            with mock.patch.object(time, "sleep"):
                ret = utils.check_neutron_agent_list(
                    "url",
                    "headers",
                    host_name,
                    agent_type,
                    action=virt_const.ACTIVATION)
                self.assertFalse(ret)

    def test_check_neutron_agent_list_during_activation_success(self):
        resp = MagicMock()
        fake_agents = self._fake_neutron_agents()
        fake_agents["agents"][0]["alive"] = True
        resp.json.return_value = fake_agents
        with mock.patch.object(utils.requests, "get") as req_get:
            req_get.return_value = resp
            host_name = fake_agents["agents"][0]["host"]
            agent_type = fake_agents["agents"][0]["agent_type"]
            ret = utils.check_neutron_agent_list(
                "url",
                "headers",
                host_name,
                agent_type,
                action=virt_const.ACTIVATION)
            self.assertTrue(ret)

    def test_check_neutron_agent_list_actn_success_hostname_in_diff_case(self):
        resp = MagicMock()
        fake_agents = self._fake_neutron_agents()
        fake_agents["agents"][0]["alive"] = True
        resp.json.return_value = fake_agents
        with mock.patch.object(utils.requests, "get") as req_get:
            req_get.return_value = resp
            host_name = fake_agents["agents"][0]["host"].upper()
            agent_type = fake_agents["agents"][0]["agent_type"]
            ret = utils.check_neutron_agent_list(
                "url",
                "headers",
                host_name,
                agent_type,
                action=virt_const.ACTIVATION)
            self.assertTrue(ret)

    def test_check_neutron_agent_list_empty_fail(self):
        org_api_time = utils.NEUTRON_API_RETRY_INTERVAL
        org_max_time = utils.NEUTRON_MAX_TIMEOUT
        resp = MagicMock()
        fake_agents_empty = self._fake_neutron_agents_empty()
        fake_agents = self._fake_neutron_agents()
        resp.json.return_value = fake_agents_empty
        with mock.patch.object(utils.requests, "get") as req_get:
            utils.NEUTRON_API_RETRY_INTERVAL = 1
            utils.NEUTRON_MAX_TIMEOUT = 1
            req_get.return_value = resp
            host_name = fake_agents["agents"][0]["host"]
            agent_type = fake_agents["agents"][0]["agent_type"]
            ret = utils.check_neutron_agent_list(
                "url",
                "headers",
                host_name,
                agent_type,
                action=virt_const.ACTIVATION)

            utils.NEUTRON_API_RETRY_INTERVAL = org_api_time
            utils.NEUTRON_MAX_TIMEOUT = org_max_time
            self.assertFalse(ret)

    def test_check_neutron_agent_list_during_deactivation_success(self):
        resp = MagicMock()
        fake_agents = self._fake_neutron_agents()
        fake_agents["agents"][0]["alive"] = False
        resp.json.return_value = fake_agents
        with mock.patch.object(utils.requests, "get") as req_get:
            req_get.return_value = resp
            host_name = fake_agents["agents"][0]["host"]
            agent_type = fake_agents["agents"][0]["agent_type"]
            ret = utils.check_neutron_agent_list(
                "url",
                "headers",
                host_name,
                agent_type,
                action=virt_const.DEACTIVATION)
            self.assertTrue(ret)

    def test__check_neutron_agent_status_True(self):
        agents = [{"host": "proxy_name.hpiscmgmt.local",
                        "agent_type": "HP ISC L2 Agent",
                        "alive": True}]
        host_name = "proxy_name.hpiscmgmt.local"
        agent_type = "HP ISC L2 Agent"
        val = utils._check_neutron_agent_status(agents, host_name, agent_type)
        self.assertTrue(val)

    def test__check_neutron_agent_status_False(self):
        agents = [{"host": "proxy_name.hpiscmgmt.local",
                        "agent_type": "HP ISC L2 Agent",
                        "alive": True}]
        host_name = "proxy_name.hpiscmgmt.local"
        agent_type = "HP ISC L3 Agent"
        val = utils._check_neutron_agent_status(agents, host_name, agent_type)
        self.assertFalse(val)

    def test_get_nova_hypervisor_rest_api(self):
        auth_dict = {'tenant_id': "tenant_id", "auth_token": "xyz"}
        fake_header = self._fake_nova_header()
        context = MagicMock()
        expected_url = "http://10.10.10.10:8774/v1.1/tenant_id/os-hypervisors"
        with mock.patch.object(context_, "get_service_auth_info") as m_auth:
            m_auth.return_value = auth_dict
            result = utils.get_nova_hypervisor_rest_api(context, "10.10.10.10")
            res = cmp((expected_url, fake_header), result)
            self.assertFalse(res == 0)

    def test_get_nova_hypervisor_show_api(self):
        auth_dict = {'tenant_id': "tenant_id", "auth_token": "xyz"}
        fake_header = self._fake_nova_header()
        context = MagicMock()
        expected_url = "http://10.10.10.10:8774/v1.1/tenant_id/os-hypervisors"
        with mock.patch.object(context_, "get_service_auth_info") as m_auth:
            m_auth.return_value = auth_dict
            result = utils.get_nova_hypervisor_show_api(context, "10.10.10.10")
            res = cmp((expected_url, fake_header), result)
            self.assertFalse(res == 0)

    def test_get_neutron_agent_rest_api(self):
        auth_dict = {'tenant_id': "tenant_id", "auth_token": "xyz"}
        fake_header = self._fake_neutron_header()
        context = MagicMock()
        expected_url = "http://10.10.10.10:8774/v2.0/agents.json"
        with mock.patch.object(context_, "get_service_auth_info") as m_auth:
            m_auth.return_value = auth_dict
            result = utils.get_neutron_agent_rest_api(context, "10.10.10.10")
            res = cmp((expected_url, fake_header), result)
            self.assertFalse(res == 0)

    def test_validate_nova_neutron_list_check_for_nova(self):
        hypervisor_hostname = "hypervisor_hostname"
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_nova_hypervisor_rest_api"),
                mock.patch.object(utils, "get_nova_hypervisor_info"),
                mock.patch.object(requests, "get")
                ) as(get_cont, exp_inp_mod, nova_hyp_api,
                      nova_hyp_id, req_m):
                get_cont.return_value = fake_data.cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova
                expected_url = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-hypervisors"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response
                req_m.return_value = fake_response
                nova_hyp_id.return_value = 0
                self.assertRaises(exception.NovaHypervisorNotFoundException,
                                  utils.validate_nova_neutron_list,
                                  self.context, "id", self.db_api,
                                  hypervisor_hostname, None,
                                  constants.ACTIVATION, False)

    def test_validate_nova_neutron_list_check_for_neutron(self):
        hypervisor_hostname = "hypervisor_hostname"
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_nova_hypervisor_rest_api"),
                mock.patch.object(utils, "get_nova_hypervisor_info"),
                mock.patch.object(utils, "get_neutron_agent_rest_api"),
                mock.patch.object(requests, "get"),
                mock.patch.object(utils, "check_neutron_agent_list")
                ) as(get_cont, exp_inp_mod, nova_hyp_api,
                     nova_hyp_id, neutron_agent_api, req_m,
                     neutron_agent_list):
                get_cont.return_value = fake_data.cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova_neutron
                expected_url = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-hypervisors"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response
                req_m.return_value = fake_response
                nova_hyp_id.return_value = 2
                expected_url = "http://10.10.10.10:8774/v2.0/agents.json"
                neutron_agent_api.return_value = (expected_url,
                                                self._fake_neutron_header())
                neutron_agent_list.return_value = False
                self.assertRaises(
                                  exception.NeutronAgentNotFoundException,
                                  utils.validate_nova_neutron_list,
                                  self.context, "id", self.db_api,
                                  hypervisor_hostname, None,
                                  constants.ACTIVATION, True)

    def test_check_for_running_vms(self):
        hypervisor_hostname = "hypervisor_hostname"
        resource_inventory = fake_data.resource_inventory
        cont = [{"name": "ccp"}]
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_nova_hypervisor_show_api"),
                mock.patch.object(requests, "get")
                ) as(get_cont, exp_inp_mod, nova_hyp_api,
                     req_m):
                get_cont.return_value = cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova
                expected_url = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-hypervisors"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response_2
                req_m.return_value = fake_response
                self.assertRaises(exception.DeactivationFailure,
                                  utils.check_for_running_vms,
                                  self,
                                  self.context, hypervisor_hostname,
                                  resource_inventory)

    def test_check_for_running_vms_connection_error(self):
        hypervisor_hostname = "hypervisor_hostname"
        resource_inventory = fake_data.resource_inventory
        cont = [{"name": "ccp"}]
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_nova_hypervisor_show_api"),
                mock.patch.object(requests, "get")
                ) as(get_cont, exp_inp_mod, nova_hyp_api,
                     req_m):
                get_cont.return_value = cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova
                expected_url = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-hypervisors"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response_2
                req_m.return_value = fake_response
                req_m.side_effect = requests.exceptions.ConnectionError
                self.assertRaises(requests.exceptions.ConnectionError,
                                  utils.check_for_running_vms,
                                  self,
                                  self.context, hypervisor_hostname,
                                  resource_inventory)

    def test_check_for_running_vms_hostname_in_different_case(self):
        hypervisor_hostname = "hypervisor_hostname"
        resource_inventory = fake_data.resource_inventory
        cont = [{"name": "ccp"}]
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_nova_hypervisor_show_api"),
                mock.patch.object(requests, "get")
                ) as(get_cont, exp_inp_mod, nova_hyp_api,
                     req_m):
                get_cont.return_value = cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova
                expected_url = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-hypervisors"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response_3
                req_m.return_value = fake_response
                self.assertRaises(exception.DeactivationFailure,
                                  utils.check_for_running_vms,
                                  self,
                                  self.context, hypervisor_hostname,
                                  resource_inventory)

    def test_check_for_running_vms_no_exception(self):
        hypervisor_hostname = "hypervisor_hostname"
        resource_inventory = fake_data.resource_inventory
        cont = [{"name": "ccp"}]
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_nova_hypervisor_show_api"),
                mock.patch.object(requests, "get")
                ) as(get_cont, exp_inp_mod, nova_hyp_api,
                     req_m):
                get_cont.return_value = cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova
                expected_url = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-hypervisors"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response_4
                req_m.return_value = fake_response
                utils.check_for_running_vms(self,
                                  self.context, hypervisor_hostname,
                                  resource_inventory)

    def test_get_headers_is_not_none(self):
        self.context.auth_token = "fake_auth_token"
        headers = utils.get_headers(self.context)
        self.assertNotEqual(None, headers)

    def test_get_headers_is_none(self):
        self.context.auth_token = ""
        headers = utils.get_headers(self.context)
        self.assertEqual(None, headers)

    def test_check_ovsvapp_agent_status(self):
        ovsvapp_names = ['ovs-1-2-2-2']
        agents = MagicMock()
        self.assertFalse(utils.check_ovsvapp_agent_status(agents,
                                                          ovsvapp_names))

    def _test_check_ovsvapp_agent_status_is_none(self):
        fake_data1 = {"agents": [
                        {"binary": "hpvcn-neutron-agent",
                         "alive": False,
                         "host": "ovsvapp-10-1-214-177",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.177"}
                         },
                       {"binary": "hpvcn-neutron-agent",
                         "alive": False,
                         "host": "ovsvapp-10-1-214-178",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.178"}
                         },

                        ]
            }

        agents = fake_data1.get("agents")
        ovsvapp_names = ["10.1.214.177",
                         "10.1.214.178"]
        self.assertIsNone(utils.check_ovsvapp_agent_status(agents,
                                                           ovsvapp_names))

    def test_check_ovsvapp_agent_status_failure(self):
        fake_data1 = {"agents": [
                        {"binary": "hpvcn-neutron-agent",
                         "alive": False,
                         "host": "ovsvapp-10-1-214-177",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.177"}
                         },
                       {"binary": "hpvcn-neutron-agent",
                         "alive": False,
                         "host": "ovsvapp-10-1-214-178",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.178"}
                         },

                        ]
            }

        agents = fake_data1.get("agents")
        ovsvapp_names = ["10.1.214.179",
                         "10.1.214.180"]
        self.assertFalse(utils.check_ovsvapp_agent_status(agents,
                                                           ovsvapp_names))

    def test_check_ovsvapp_agent_status_success(self):
        fake_data1 = {"agents": [
                        {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "host": "ovsvapp-10-1-214-177",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.177"},
                         },
                       {"binary": "hpvcn-neutron-agent",
                         "alive": True,
                         "host": "ovsvapp-10-1-214-178",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.178"}
                         },

                        ]
            }
        agents = fake_data1.get("agents")
        ovsvapp_names = ["10.1.214.177",
                         "10.1.214.178"]
        success = [' 10.1.214.177 on the host 10.1.214.177 is up and running ',
                   ' 10.1.214.178 on the host 10.1.214.178 is up and running ']
        self.assertEquals(success, utils.check_ovsvapp_agent_status(
            agents, ovsvapp_names))

    def test_check_ovsvapp_agent_status_error_by_none(self):
        fake_data1 = {"agents": [
                        {"binary": "hpvcn-neutron-agent",
                         "alive": False,
                         "host": "ovsvapp-10-1-214-177",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.177"},
                         },
                       {"binary": "hpvcn-neutron-agent",
                         "alive": False,
                         "host": "ovsvapp-10-1-214-178",
                         "agent_type": "OVSvApp Agent",
                         "configurations": {"esx_host_name": "10.1.214.178"}
                         },

                        ]
            }

        agents = fake_data1.get("agents")
        ovsvapp_names = ["10.1.214.177",
                         "10.1.214.178"]
        self.assertIsNone(utils.check_ovsvapp_agent_status(agents,
                                                           ovsvapp_names))

    def test_check_ovsvapp_agent_list_failure(self):
        resource_inventory = fake_data.resource_inventory2
        hypervisor_hostname = "hypervisor_hostname"
        cont = [{"name": "ccp"}]
        expected_url = "http://10.10.10.10:8774/v1.1/tenant_id/os-hypervisors"
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_neutron_agent_rest_api"),
                mock.patch.object(requests, "get"),
                mock.patch.object(utils, "check_ovsvapp_agent_status"),
                ) as(get_cont, exp_inp_mod, neutron_agent_rest_api,
                     req_m, ovsvapp_agent_status):
                get_cont.return_value = cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova_neutron
                neutron_agent_rest_api.return_value = (expected_url,
                                                self._fake_neutron_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response_2
                req_m.return_value = fake_response
                req_m.side_effect = requests.exceptions.ConnectionError
                with mock.patch.object(time, "sleep"):
                    ovsvapp_agent_status.return_value = None
                    self.assertRaises(exception.OVSvAPPNotUpException,
                                  utils.check_ovsvapp_agent_list,
                                  self.context,
                                  hypervisor_hostname,
                                  resource_inventory)

    def test_check_ovsvapp_agent_list_success(self):
        resource_inventory = fake_data.resource_inventory2
        hypervisor_hostname = "hypervisor_hostname"
        cont = [{"name": "ccp"}]
        expected_url = "http://10.10.10.10:8774/v1.1/tenant_id/os-hypervisors"
        with mock.patch.object(hlm_facade_handler,
                                "HLMFacadeWrapper") as hlm_f:
            self.hux = hlm_f.return_value = self.mock_obj
            with contextlib.nested(
                mock.patch.object(self.hux, "get_controlplanes"),
                mock.patch.object(self.hux, "get_model_expanded"),
                mock.patch.object(utils, "get_neutron_agent_rest_api"),
                mock.patch.object(requests, "get"),
                mock.patch.object(utils, "check_ovsvapp_agent_status"),
                ) as(get_cont, exp_inp_mod, neutron_agent_rest_api,
                     req_m, ovsvapp_agent_status):
                get_cont.return_value = cont
                exp_inp_mod.return_value = fake_data.exp_inp_nova_neutron
                neutron_agent_rest_api.return_value = (expected_url,
                                                self._fake_neutron_header())
                fake_response = self.mock_obj
                fake_response.json = self._fake_json_response_6
                req_m.return_value = fake_response
                with mock.patch.object(time, "sleep"):
                    ovsvapp_agent_status.return_value = [
                    'ovsvapp-10-1-214-177 on the host'
                    '10.1.214.177 is up and running ',
                    'ovsvapp-10-1-214-178 on the host'
                    '10.1.214.178 is up and running ']
                    ovsvapp_agent_list = utils.check_ovsvapp_agent_list(
                        self.context, hypervisor_hostname,
                        resource_inventory)
                    self.assertNotEqual(ovsvapp_agent_list, None)

    @mock.patch("eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper."
                "get_controlplanes")
    def test_get_hypervisor_role(self, m_control_plane):
        m_control_plane.return_value = fake_data.fake_control_plance
        hux_obj = hlm_facade_handler.HLMFacadeWrapper(fake_data.FakeContext())
        role = utils.get_hypervisor_roles(hux_obj,
                                          constants.EON_RESOURCE_TYPE_HLINUX)
        self.assertEquals(role[0], "KVM-COMPUTE-ROLE-NO-BOND-2-DISKS")
        role = utils.get_hypervisor_roles(hux_obj,
                                          constants.EON_RESOURCE_TYPE_RHEL)
        self.assertEquals(role[0], "KVM-COMPUTE-ROLE-NO-BOND-2-DISKS")
        role = utils.get_hypervisor_roles(hux_obj,
                                          constants.EON_RESOURCE_TYPE_HYPERV)
        self.assertEquals(role[0], "HYPERV-COMPUTE-ROLE-NO-BOND")

    def test_get_nova_hypervisor_service_api(self):
        auth_dict = {'tenant_id': "tenant_id", "auth_token": "xyz"}
        context = MagicMock()
        id = '1234'
        url = "http://10.10.10.10:8774/v2.1/tenant_id/os-services/1234"
        with mock.patch.object(context_, "get_service_auth_info") as m_auth:
            m_auth.return_value = auth_dict
            result = utils.get_nova_hypervisor_service_api(context,
                                        "http://10.10.10.10:8774", id)
            res = cmp(url, result)
            self.assertTrue(res == 0)

    def test_get_neutron_agent_list(self):
        url = "http://10.10.10.10:8774/v2/tenant_id/os-services/1234"
        headers = {}
        context = MagicMock()
        with contextlib.nested(
                mock.patch.object(utils, "get_neutron_url"),
                mock.patch.object(utils, "get_neutron_agent_rest_api"),
                mock.patch.object(requests, "get"),
                ) as(neut_url, neut_rest_api, req_m):
            neut_url.return_value = url
            neut_rest_api.return_value = (url, headers)
            fake_response = self.mock_obj
            fake_response.json = self._fake_json_response_8
            req_m.return_value = fake_response
            agents = fake_data.agents
            self.assertEquals(agents,
                     utils.get_neutron_agent_list(self, context))

    def test_get_nova_url(self):
        context = MagicMock()
        url = CONF.nova.url
        nova_url = utils.get_nova_url(context)
        self.assertEquals(url, nova_url)

    def test_get_nova_hypervisor_list_success(self):
        nova_url = "http://10.10.10.10:8774/"
        headers = {}
        hyp = fake_data.hyp
        with mock.patch.object(requests, "get") as req_m:
            fake_response = self.mock_obj
            fake_response.json = self._fake_json_response_7
            req_m.return_value = fake_response
            self.assertEquals(hyp, utils.get_nova_hypervisor_list(nova_url,
                                                                  headers))

    def test_get_nova_hypervisor_list_failure(self):
        nova_url = "http://10.10.10.10:8774/"
        headers = {}
        with mock.patch.object(requests, "get") as req_m:
            fake_response = self.mock_obj
            fake_response.json = self._fake_json_response_7
            req_m.return_value = fake_response
            req_m.side_effect = requests.exceptions.ConnectionError
            self.assertRaises(requests.exceptions.ConnectionError,
                              utils.get_nova_hypervisor_list,
                              nova_url, headers)

    def test_delete_nova_service_success(self):
        hypervisor_hostname = "hypervisor_hostname"
        context = MagicMock()
        with contextlib.nested(
                mock.patch.object(utils, "get_nova_url"),
                mock.patch.object(utils, "get_nova_hypervisor_show_api"),
                mock.patch.object(utils, "get_nova_hypervisor_list"),
                mock.patch.object(utils, "get_nova_hypervisor_service_api"),
                mock.patch.object(requests, "delete")
                ) as(nova_url, nova_hyp_api, nova_hyp_list, nova_serv_api,
                      req_d):
                nova_url.return_value = "http://10.10.10.10:8774/"
                expected_url = "http://10.10.10.10:8774/v2.1/"
                "tenant_id/os-hypervisorrs/detail"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                nova_hyp_list.return_value = fake_data.hyp
                nova_serv_api.return_value = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-details"
                fake_response = self.mock_obj
                fake_response.status_code = 204
                req_d.return_value = fake_response
                nova_result = utils.delete_nova_service(context,
                                                         hypervisor_hostname)
                self.assertTrue(nova_result)

    def test_delete_nova_service_no_service_failure(self):
        hypervisor_hostname = "hyspervisor_hostname"
        context = MagicMock()
        with contextlib.nested(
                mock.patch.object(utils, "get_nova_url"),
                mock.patch.object(utils, "get_nova_hypervisor_show_api"),
                mock.patch.object(utils, "get_nova_hypervisor_list"),
                mock.patch.object(utils, "get_nova_hypervisor_service_api"),
                mock.patch.object(requests, "delete")
                ) as(nova_url, nova_hyp_api, nova_hyp_list, nova_serv_api,
                      req_d):
                nova_url.return_value = "http://10.10.10.10:8774/"
                expected_url = "http://10.10.10.10:8774/v2.1/tenant_id/"
                "os-hypervisorrs/detail"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                nova_hyp_list.return_value = fake_data.hyp1
                fake_response = self.mock_obj
                nova_serv_api.return_value = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-details"
                fake_response.status_code = 204
                req_d.return_value = fake_response
                nova_result = utils.delete_nova_service(context,
                                                         hypervisor_hostname)
                self.assertFalse(nova_result)

    def test_delete_nova_service_REST_failure(self):
        hypervisor_hostname = "hypervisor_hostname"
        context = MagicMock()
        with contextlib.nested(
                mock.patch.object(utils, "get_nova_url"),
                mock.patch.object(utils, "get_nova_hypervisor_show_api"),
                mock.patch.object(utils, "get_nova_hypervisor_list"),
                mock.patch.object(utils, "get_nova_hypervisor_service_api"),
                mock.patch.object(requests, "delete")
                ) as(nova_url, nova_hyp_api, nova_hyp_list, nova_serv_api,
                      req_d):
                nova_url.return_value = "http://10.10.10.10:8774/"
                expected_url = "http://10.10.10.10:8774/v2.1/tenant_id/"
                "os-hypervisorrs/detail"
                nova_hyp_api.return_value = (expected_url,
                self._fake_nova_header())
                nova_hyp_list.return_value = fake_data.hyp
                fake_response = self.mock_obj
                nova_serv_api.return_value = "http://10.10.10.10:8774/v1.1/"
                "tenant_id/os-details"
                fake_response.status_code = 203
                req_d.return_value = fake_response
                nova_result = utils.delete_nova_service(context,
                                                         hypervisor_hostname)
                self.assertFalse(nova_result)

    def test_delete_neutron_service_success(self):
        hypervisor_hostname = "hypervisor_hostname"
        context = MagicMock()
        url = "http://10.10.10.10:8774/v1.1/"
        "tenant_id/os-details"
        headers = {}
        with contextlib.nested(
                mock.patch.object(utils, "get_neutron_url"),
                mock.patch.object(utils, "get_neutron_agent_list"),
                mock.patch.object(utils, "get_neutron_agent_rest_api"),
                mock.patch.object(requests, "delete")
                ) as(neut_url, neut_agen_list, neut_agen_api,
                      req_d):
                neut_url.return_value = "http://10.10.10.10:8774/"
                neut_agen_list.return_value = fake_data.agents
                neut_agen_api.return_value = url, headers
                fake_response = self.mock_obj
                fake_response.status_code = 204
                req_d.return_value = fake_response
                neut_result = utils.delete_neutron_service(self, context,
                                                         hypervisor_hostname)
                self.assertEquals(None, neut_result)

    def test_delete_neutron_service_failure_rest_call(self):
        hypervisor_hostname = "hypervisor_hostname"
        context = MagicMock()
        url = "http://10.10.10.10:8774/v1.1/"
        "tenant_id/os-details"
        headers = {}
        with contextlib.nested(
                mock.patch.object(utils, "get_neutron_url"),
                mock.patch.object(utils, "get_neutron_agent_list"),
                mock.patch.object(utils, "get_neutron_agent_rest_api"),
                mock.patch.object(requests, "delete")
                ) as(neut_url, neut_agen_list, neut_agen_api,
                      req_d):
                neut_url.return_value = "http://10.10.10.10:8774/"
                neut_agen_list.return_value = fake_data.agents
                neut_agen_api.return_value = url, headers
                fake_response = self.mock_obj
                fake_response.status_code = 404
                req_d.return_value = fake_response
                neut_result = utils.delete_neutron_service(self, context,
                                                         hypervisor_hostname)
                self.assertFalse(neut_result)

    def test_delete_neutron_service_failure_empty_neutron_list(self):
        hypervisor_hostname = "hypervisor_hostname"
        context = MagicMock()
        with contextlib.nested(
                mock.patch.object(utils, "get_neutron_url"),
                mock.patch.object(utils, "get_neutron_agent_list")
                ) as(neut_url, neut_agen_list):
                neut_url.return_value = "http://10.10.10.10:8774/"
                neut_agen_list.return_value = []
                neut_result = utils.delete_neutron_service(self, context,
                                                         hypervisor_hostname)
                self.assertFalse(neut_result)
