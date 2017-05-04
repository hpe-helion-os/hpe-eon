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

import json
import logging as default_log
import requests
from eon.hlm_facade import exception as facade_exception
from eon.openstack.common import log as logging

LOG = logging.getLogger(__name__)
default_log.getLogger("requests").setLevel("WARNING")
SECRET = "***"


def _log(method, req_url, headers, req_body):
    # base curl command
    curl = ['curl -i -X %s' % method]
    # headers as part of curl command
    for key, value in headers.items():
        # mask only auth token with SECRET
        if key == 'X-Auth-Token':
            header = '-H \'%s: %s\'' % (key, SECRET)
        else:
            header = '-H \'%s: %s\'' % (key, value)
        curl.append(header)
    # body as part of curl command
    if req_body:
        curl.append('-d \'%s\'' % req_body)
    # end-point url as part of curl command
    curl.append('%s' % req_url)

    # mask passwords
    curl_string = logging.mask_password(' '.join(curl))
    LOG.debug(curl_string)


def _http_request(method, req_url, headers=None, body=None):
    """ A simple HTTP request interface
    """
    if not headers:
        headers = {}
    headers['Content-Type'] = "application/json"
    headers['Accept'] = "application/json"
    if body:
        body = json.dumps(body)
    try:
        _log(method, req_url, headers, body)
        resp = requests.request(method,
                                req_url,
                                headers=headers,
                                data=body)
    except Exception:
        raise

    LOG.debug("RESP: %s" % resp)
    if resp.text:
        fin_resp = resp.json()
    else:
        fin_resp = resp

    if resp.status_code == requests.codes.unauthorized:
        raise facade_exception.Unauthorized()
    elif resp.status_code == requests.codes.not_found:
        message = fin_resp.get('message')
        raise facade_exception.NotFound(message)

    if 400 <= resp.status_code < 600:
        LOG.warn("hlm-ux-services request returned failure status: %s"
                 % resp.status_code)
        message = fin_resp.get('message')
        raise facade_exception.HlmFacadeException(message)

    return fin_resp


def post(url, body, headers=None):
    return _http_request('POST', url, headers, body)


def get(url, headers=None):
    return _http_request('GET', url, headers)


def delete(url, headers=None):
    return _http_request('DELETE', url, headers)


def put(url, body, headers=None):
    return _http_request('PUT', url, headers, body)
