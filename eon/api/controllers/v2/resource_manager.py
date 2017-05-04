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

import pecan
from pecan import rest

from eon import api
from eon import validators

RESOURCE_MANAGER = "resource_mgrs"


class ResourceManager(rest.RestController):

    # Version 1.0: initial version - CRUD APIs
    def __init__(self):
        self.validator = validators.ResourceManagerValidator()

    @pecan.expose('json')
    @api.handle_exceptions()
    def get_all(self, **kwargs):
        """Returns all the resource managers or
        the filtered resource mgrs based on the query parameter
        :param: keyword arguments for querying
        :return [
                    {"1": "b",
                    "id": "xyz",
                    "2": "y",
                    },

                    {"1": "x",
                     "2": "y",
                     "id": "xya",
                    }
                ]
        """
        api.load_query_params(kwargs, self.validator.validate_get)
        type_ = kwargs.get("type")
        return pecan.request.rpcapi_v2.get_all_resource_mgrs(
            pecan.request.context, type_)

    @pecan.expose('json')
    @api.handle_exceptions()
    def get(self, res_mgr_id):
        validators.assert_is_valid_uuid_from_uri(res_mgr_id)
        return pecan.request.rpcapi_v2.get_resource_mgr(
            pecan.request.context, res_mgr_id)

    @pecan.expose('json')
    @api.handle_exceptions()
    def post(self):
        req = pecan.request
        data = api.load_body(req, validator=self.validator.validate_post)
        return pecan.request.rpcapi_v2.create_resource_mgr(
            pecan.request.context, data)

    @pecan.expose('json')
    @api.handle_exceptions()
    def put(self, res_mgr_id):
        validators.assert_is_valid_uuid_from_uri(res_mgr_id)
        req = pecan.request
        data = api.load_body(req, validator=self.validator.validate_put)
        return pecan.request.rpcapi_v2.update_resource_mgr(
            pecan.request.context, res_mgr_id, data)

    @pecan.expose('json')
    @api.handle_exceptions()
    def delete(self, res_mgr_id):
        validators.assert_is_valid_uuid_from_uri(res_mgr_id)
        return pecan.request.rpcapi_v2.delete_resource_mgr(
            pecan.request.context, res_mgr_id)
