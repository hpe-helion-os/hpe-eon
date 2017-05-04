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

from mock import patch
from mock import call
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.hlm_facade import exception
from eon.hlm_facade import constants

URL = "http://localhost:9085"
fake_id = "rand"


class TestHTTPRequests(base_test.TestCase):

    def setUp(self):
        super(TestHTTPRequests, self).setUp()
        self.context.auth_token = "m1a4y1a9n3k"
        self.hux = HLMFacadeWrapper(self.context)
        self.headers = {'X-Auth-Token': self.context.auth_token}

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_model(self, mock_req):
        url = URL + constants.INPUT_MODEL_URL
        self.hux.get_model()
        mock_req.assert_called_once_with(url, headers=self.headers)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_model_expanded(self, mock_req):
        url = URL + constants.EXPANDED_INPUT_MODEL_URL
        self.hux.get_model_expanded()
        mock_req.assert_called_once_with(url, headers=self.headers)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_model_expanded_id(self, mock_req):
        url = URL + constants.EXPANDED_INPUT_MODEL_SERVERS + "/" + fake_id
        self.hux.get_model_expanded(fake_id)
        mock_req.assert_called_once_with(url, headers=self.headers)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_servers(self, mock_req):
        url = URL + constants.SERVERS_URL
        self.hux.get_servers()
        mock_req.assert_called_once_with(url, headers=self.headers)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_hostnames(self, mock_cp_out):
        mock_cp_out.return_value = {
            "ccn-01": {
                  "hostname": "ccn-host1", 'server_role': 'esx_role'},
            "ccn-02": {
                  "hostname": "ccn-host2", 'server_role': 'ovsvapp_role'}
            }
        url = URL + constants.CP_OUTPUT_SERVER_INFO
        servers = self.hux.get_hostnames()
        mock_cp_out.assert_called_once_with(url, headers=self.headers)
        exp_server_hostnames = {'ccn-02': 'ccn-host2', 'ccn-01': 'ccn-host1'}
        self.assertDictEqual(exp_server_hostnames, servers)

    @patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.get_hostnames')
    def test_model_generated_host_name_id(self, mock_get_hostnames):
        mock_get_hostnames.return_value = {'id1': 'host1', 'id2': 'host2'}
        hostname = self.hux.model_generated_host_name('id2')
        self.assertEqual(hostname, 'host2')

    @patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.get_hostnames')
    def test_model_generated_host_name_ids(self, mock_get_hostnames):
        mock_get_hostnames.return_value = {'id1': 'host1', 'id2': 'host2'}
        hostnames = self.hux.model_generated_host_name(['id1', 'id2'])
        self.assertEqual(hostnames, 'host1,host2')

    @patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.get_servers')
    def test_get_server_by_role(self, mock_get_server):
        mock_get_server.return_value = [
            {"id": "deployer",
             "role": "HLM-ROLE"
             },
            {"id": "ccn1-0001",
             "role": "MANAGEMENT-ROLE"
             },
            {"id": "ccn2-0001",
             "role": "MONITORING-ROLE"
             },
        ]
        servers_with_the_same_role = self.hux.get_server_by_role(
            "MANAGEMENT-ROLE")
        mock_get_server.assert_called_once_with()
        self.assertEquals(servers_with_the_same_role[0]["id"], "ccn1-0001")

    @patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.get_servers')
    def test_get_server_by_role_empty_list(self, mock_get_server):
        mock_get_server.return_value = [
            {"id": "deployer",
             "role": "HLM-ROLE"
             },
            {"id": "ccn2-0001",
             "role": "MONITORING-ROLE"
             },
        ]
        servers_with_the_same_role = self.hux.get_server_by_role(
            "MANAGEMENT-ROLE")
        mock_get_server.assert_called_once_with()
        self.assertEquals(len(servers_with_the_same_role), 0)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_server_by_id(self, mock_req):
        url = URL + constants.SERVERS_URL + "/" + fake_id
        self.hux.get_server_by_id(fake_id)
        mock_req.assert_called_once_with(url, headers=self.headers)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_server_by_id_exception(self, mock_req):
        mock_req.side_effect = Exception
        self.assertRaises(Exception, self.hux.get_server_by_id, fake_id)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_interfaces_by_id(self, mock_req):
        url = URL + constants.INTERFACES_URL + "/" + fake_id
        self.hux.get_interfaces_by_id(fake_id)
        mock_req.assert_called_once_with(url, headers=self.headers)

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_interfaces_by_id_exception(self, mock_req):
        mock_req.side_effect = Exception
        self.assertRaises(Exception, self.hux.get_interfaces_by_id, fake_id)

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_update_servers(self, mock_get, mock_put, mock_post):
        mock_get.return_value = [{'fake_key': 'fake_val'}]
        body = {"key": "val"}
        self.hux.create_server(body)

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_update_server_by_id(self, mock_get, mock_put, mock_post):
        mock_get.return_value = {}
        body = {"key": "val"}
        self.hux.update_server_by_id(body, fake_id)

    @patch('eon.hlm_facade.http_requests.delete')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_update_servers_exception(self, mock_get, mock_put, mock_delete):
        body = {"key": "val"}
        mock_put.side_effect = Exception
        self.assertRaises(Exception, self.hux.create_server, body)

    @patch('eon.hlm_facade.http_requests.delete')
    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_update_server_by_id_exception(self, mock_get, mock_put, mock_post,
                                           mock_delete):
        body = {"key": "val"}
        mock_put.side_effect = exception.UpdateException
        self.assertRaises(exception.UpdateException,
                          self.hux.update_server_by_id, body, fake_id)

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_config_processor_run(self, mock_get, mock_put, mock_post):
        mock_post.return_value = {'pRef': "ascascas-vdevd"}
        mock_get.return_value = {"code": 0}
        self.hux.config_processor_run()

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_config_processor_run_exception(self, mock_get, mock_put,
                                            mock_post):
        mock_post.return_value = {'pRef': "ascascas-vdevd"}
        self.assertRaises(Exception, self.hux.config_processor_run)

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_ready_deployment(self, mock_get, mock_put, mock_post):
        mock_post.return_value = {'pRef': "ascascas-vdevd"}
        mock_get.return_value = {"code": 0}
        self.hux.ready_deployment()

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.put')
    @patch('eon.hlm_facade.http_requests.get')
    def test_ready_deployment_exception(self, mock_get, mock_put, mock_post):
        mock_post.return_value = {'pRef': "ascascas-vdevd"}
        self.assertRaises(Exception, self.hux.ready_deployment)

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.get')
    def test_run_playbook(self, mock_get, mock_post):
        mock_get.side_effect = [{'hostname': 'test-dcm-conf'}, {'code': 0}]
        mock_post.return_value = {'pRef': 'rand'}
        self.hux.run_playbook('site', fake_id)

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.get')
    def test_run_playbook_post_deactivate(self, mock_get, mock_post):
        mock_get.side_effect = [{'hostname': 'test-dcm-conf'}, {'code': 0}]
        mock_post.return_value = {'pRef': 'rand'}
        self.hux.run_playbook('hlm_post_deactivation', fake_id)

    @patch('eon.hlm_facade.http_requests.delete')
    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.get')
    def test_run_playbook_timeout(self, mock_get, mock_post, mock_del):
        mock_get.side_effect = [{'hostname': 'test-dcm-conf'}, {}, {}]
        mock_post.return_value = {'pRef': 'rand'}
        self.assertRaises(exception.TimeoutError, self.hux.run_playbook,
                          'site', fake_id, retries=2)
        expected_url = URL + constants.PLAYS + "/rand"
        mock_del.assert_called_once_with(expected_url,
                             headers={'X-Auth-Token': 'm1a4y1a9n3k'})

    @patch('eon.hlm_facade.http_requests.delete')
    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.get')
    def test_run_playbook_timeout_process_not_found(self, mock_get,
                                                    mock_post, mock_del):
        mock_get.side_effect = [{'hostname': 'test-dcm-conf'}, {}, {}]
        mock_post.return_value = {'pRef': 'rand'}
        mock_del.side_effect = [exception.NotFound]
        self.assertRaises(exception.TimeoutError, self.hux.run_playbook,
                          'site', fake_id, retries=2)
        expected_url = URL + constants.PLAYS + "/rand"
        mock_del.assert_called_once_with(expected_url,
                             headers={'X-Auth-Token': 'm1a4y1a9n3k'})

    @patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper._get_status')
    @patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper._run')
    def test_run_playbook_localhost(self, mock_run, mocked_get_status):
        extra_args = {"nodename": "rhelnode"}
        self.hux.run_playbook('hlm_remove_cobbler_node', extra_args=extra_args)
        url = ('http://localhost:9085/api/v1/hlm/playbooks/'
               'hlm_remove_cobbler_node')
        expected_body = {'limit': 'localhost'}
        expected_body.update(extra_args)
        mock_run.assert_called_once_with(url, body=expected_body)

    @patch('eon.hlm_facade.http_requests.post')
    def test_commit_changes(self, mock_post):
        self.hux.commit_changes(fake_id, "fake-task")

    @patch('eon.hlm_facade.http_requests.delete')
    def test_delete_server(self, mock_del):
        self.hux.delete_server(fake_id)
        expected_url = URL + "/api/v1/hlm/model/entities/servers/rand"
        mock_del.assert_called_once_with(expected_url, headers={
            'X-Auth-Token': 'm1a4y1a9n3k'})

    @patch('eon.hlm_facade.http_requests.get')
    def test_cobbler_deploy_status(self, mocked_httpget):
        self.assertRaises(exception.TimeoutError,
                          self.hux.cobbler_deploy_status,
                          fake_id, retries=2)
        expected_url = URL + constants.OSINSTALL
        calls = [call(expected_url, headers={
            'X-Auth-Token': 'm1a4y1a9n3k'})]
        self.assertEquals(mocked_httpget.call_count, 2)
        mocked_httpget.assert_has_calls(calls)

    @patch('eon.hlm_facade.http_requests.get')
    def test_cobbler_deploy_status_cobbler_exception(self, mocked_httpget):
        mocked_httpget.return_value = {"servers": {fake_id: "pwr_error"}}
        self.assertRaises(exception.CobblerException,
                          self.hux.cobbler_deploy_status,
                          fake_id, retries=2)
        expected_url = URL + constants.OSINSTALL
        mocked_httpget.assert_called_once_with(expected_url, headers={
            'X-Auth-Token': 'm1a4y1a9n3k'})

    @patch('eon.hlm_facade.http_requests.get')
    def test_cobbler_deploy_status_complete(self, mocked_httpget):
        mocked_httpget.return_value = {"servers": {fake_id: "complete"}}
        self.hux.cobbler_deploy_status(fake_id, retries=2)
        expected_url = URL + constants.OSINSTALL
        mocked_httpget.assert_called_once_with(expected_url, headers={
            'X-Auth-Token': 'm1a4y1a9n3k'})

    @patch('eon.hlm_facade.http_requests.get')
    def test_get_pass_through(self, mock_get):
        self.hux.get_pass_through()
        expected_url = URL + constants.PASS_THROUGH_URL
        mock_get.assert_called_once_with(expected_url, headers={
            'X-Auth-Token': 'm1a4y1a9n3k'})

    @patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
           'add_empty_pass_through')
    @patch('eon.hlm_facade.http_requests.get')
    def test_get_pass_through_not_avail(self, mock_get, mock_aept):
        mock_get.side_effect = [exception.NotFound, {'a': 'b'}]
        self.assertRaises(exception.NotFound, self.hux.get_pass_through)
        expected_url = URL + constants.PASS_THROUGH_URL
        calls = [call(expected_url, headers={'X-Auth-Token': 'm1a4y1a9n3k'})]
        self.assertEquals(mock_get.call_count, 1)
        mock_get.assert_has_calls(calls)

    @patch('eon.hlm_facade.http_requests.post')
    @patch('eon.hlm_facade.http_requests.get')
    def test_add_empty_pass_through(self, mock_get, mock_post):
        mock_get.return_value = fake_data.FAKE_INPUT_MODEL
        self.hux.add_empty_pass_through()
        expected_url = URL + constants.INPUT_MODEL_URL
        calls = [call(expected_url, headers={'X-Auth-Token': 'm1a4y1a9n3k'})]
        mock_get.assert_has_calls(calls)
        mock_post.assert_called_once_with(expected_url,
                                          body=fake_data.EMPTY_PASS_THRU,
                                          headers={'X-Auth-Token':
                                                       'm1a4y1a9n3k'})
