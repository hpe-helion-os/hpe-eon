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
import json
from pecan import rest

from eon import api
from eon import validators
from eon.api.controllers.v2 import resource_actions
from eon.common import constants
from eon.common import exception
from eon.openstack.common import log as logging

RESOURCES = "resources"
LOG = logging.getLogger(__name__)


class Resources(rest.RestController):

    # Version 1.0: initial version - CRUD APIs
    activate = resource_actions.ActivateController()
    deactivate = resource_actions.DectivateController()
    get_template = resource_actions.GetTemplateController()
    provision = resource_actions.ProvisionController()

    def __init__(self):
        self.validator = validators.ResourceValidator()
        self.const = constants.ResourceConstants

    @pecan.expose('json')
    @api.handle_exceptions()
    def get_all(self, **kwargs):
        """Returns all the resources or
        the filtered resources based on the query parameter
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
        filters = api.load_query_params(kwargs, self.validator.validate_get)

        if self.const.LIST_SUPPORTED_TYPES in kwargs:
            return [self.const.ESXCLUSTER, self.const.HLINUX, self.const.RHEL,
                    self.const.HYPERV]

        return pecan.request.rpcapi_v2.get_all_resources(
            pecan.request.context, filters)

    @pecan.expose('json')
    @api.handle_exceptions()
    def get(self, res_id):
        """
        Return the resource
        :param res_id: resource uuid
        :returns :return
                    {"1": "x",
                     "2": "y",
                     "id": "xya",
                    }
        """
        validators.assert_is_valid_uuid_from_uri(res_id)
        return pecan.request.rpcapi_v2.get_resource(
            pecan.request.context, res_id)

    @pecan.expose('json')
    @api.handle_exceptions()
    def post(self):
        req = pecan.request
        data = api.load_body(req, validator=self.validator.validate_post)
        return pecan.request.rpcapi_v2.create_resource(
            pecan.request.context, data)

    @pecan.expose('json')
    @api.handle_exceptions()
    def put(self, res_id):
        """
        :param res_id: Resource ID
        """
        validators.assert_is_valid_uuid_from_uri(res_id)
        req = pecan.request
        data = json.loads(req.body)
        if data.get("action"):
            if data["action"] == self.const.HOST_ADD:
                LOG.info("[%s] Initiating host commission" % res_id)
                return pecan.request.rpcapi_v2.host_commission(
                    pecan.request.context, res_id, data)

            elif data["action"] == self.const.HOST_REMOVE:
                return pecan.request.rpcapi_v2.host_decommission(
                    pecan.request.context, res_id, data)
            else:
                raise exception.Invalid(_("Invalid action passed"))
        else:
            data = api.load_body(req, validator=self.validator.validate_put)
            return pecan.request.rpcapi_v2.update_resource(
                pecan.request.context, res_id, data)

    @pecan.expose('json')
    @api.handle_exceptions()
    def delete(self, res_id):
        validators.assert_is_valid_uuid_from_uri(res_id)
        return pecan.request.rpcapi_v2.delete_resource(
            pecan.request.context, res_id)
