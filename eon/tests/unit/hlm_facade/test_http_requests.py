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

from mock import patch
from eon.tests.unit import tests
from eon.hlm_facade import http_requests

FAKE_BODY = {'some_key': 'some_val'}


class fake_resp_bad_req(object):
    status_code = 400


class fake_resp_unauthorized(object):
    status_code = 401


class fake_not_found(object):
    status_code = 404


class TestHTTPRequests(tests.BaseTestCase):

    def setUp(self):
        super(TestHTTPRequests, self).setUp()
        self.url = "http://dummyURL"
        self.body = FAKE_BODY

    @patch('requests.request')
    def test__http_requests_exception(self, mock_req):
        mock_req.return_value = fake_resp_bad_req
        self.assertRaises(Exception, http_requests._http_request, 'POST',
                          self.url, headers=None, body=FAKE_BODY)

    @patch('requests.request')
    def test__http_requests(self, mock_req):
        http_requests._http_request('POST', self.url, headers=None,
                                    body=FAKE_BODY)

    @patch('requests.request')
    def test__http_requests_failed(self, mock_req):
        mock_req.side_effect = Exception
        self.assertRaises(Exception, http_requests._http_request, 'GET',
                          self.url, headers=None, body=FAKE_BODY)

    @patch('requests.request')
    def test__http_req_unauthorized(self, mock_req):
        mock_req.return_value = fake_resp_unauthorized
        self.assertRaises(Exception, http_requests._http_request, 'GET',
                          self.url, headers=None, body=FAKE_BODY)

    @patch('requests.request')
    def test__http_req_not_found(self, mock_req):
        mock_req.return_value = fake_not_found
        self.assertRaises(Exception, http_requests._http_request, 'GET',
                          self.url, headers=None, body=FAKE_BODY)

    @patch('requests.request')
    def test_post(self, mock_req):
        http_requests.post(self.url, body=FAKE_BODY)

    @patch('requests.request')
    def test_get(self, mock_req):
        http_requests.get(self.url)

    @patch('requests.request')
    def test_put(self, mock_req):
        http_requests.put(self.url, body=FAKE_BODY)

    @patch('requests.request')
    def test_delete(self, mock_req):
        http_requests.delete(self.url)
