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

import os
import pecan
import json
from pecan import rest
from pecan import expose

import eon
from eon import api
from eon import validators
from eon.openstack.common import log as logging
from eon.common import constants, exception

from oslo_config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

if (CONF.network.esx_network_driver ==
        constants.NetworkDriverConstants.OVSVAPP_NETWORK_DRIVER):
    net_template_location = (os.path.dirname(os.path.abspath(eon.__file__)) +
                             "/template/esx_network_property_template")
else:
    net_template_location = (os.path.dirname(os.path.abspath(eon.__file__)) +
                             "/template/esx_noop_network_template")


class ActivateController(rest.RestController):

    @expose(generic=True, template='json')
    def index(self):
        pass

    @index.when(method="POST", template='json')
    @api.handle_exceptions()
    def activate(self, resource_id):
        req = pecan.request
        data = api.load_body(req)
        LOG.info("Activation begins for the resource %s " % resource_id)
        return pecan.request.rpcapi_v2.activate_resource(
                pecan.request.context, resource_id,
                data)


class DectivateController(rest.RestController):
    @expose(generic=True, template='json')
    def index(self):
        pass

    @index.when(method="DELETE", template='json')
    @api.handle_exceptions()
    def deactivate(self, resource_id):
        req = pecan.request
        if req.body:
            data = api.load_body(req)
        else:
            data = dict()
        LOG.info("Deactivation begins for the resource %s " % resource_id)
        return pecan.request.rpcapi_v2.deactivate_resource(
                pecan.request.context, resource_id,
                data)


class GetTemplateController(rest.RestController):
    @expose(generic=True, template='json')
    def index(self):
        pass

    @staticmethod
    def load_json_template_with_comments(filename):
        """
        It reads a file containing json string with comments
        and returns a json object
        """
        try:
            with open(filename) as cj:
                config_json = ''.join([line.strip() for line in cj
                                   if '#' not in line.strip()])
                return json.loads(config_json)
        except IOError:
            raise exception.ValidTemplateNotFound(template=filename)

    @index.when(method="POST", template='json')
    @api.handle_exceptions()
    def get_template(self, resource_type):
        self.validator = validators.ResourceValidator()
        self.validator.validate_type(
            resource_type, constants.ResourceConstants.SUPPORTED_TYPES)
        req = pecan.request
        data = api.load_body(req)
        LOG.info("Retrieving the template for activation of type"
                 " %s" % resource_type)
        if resource_type == constants.ResourceConstants.ESXCLUSTER:
            if data:
                net_json = pecan.request.rpcapi_v2.populate_network_json(
                    pecan.request.context, resource_type,
                    data)
                if net_json:
                    net_json = json.loads(net_json)
            else:
                net_json = (GetTemplateController.
                    load_json_template_with_comments(net_template_location))
            activate_payload = constants.ResourceConstants.ACTIVATE_PAYLOAD_ESX
            activate_payload["network_properties"] = net_json
            return activate_payload
        elif resource_type == constants.ResourceConstants.RHEL:
            activate_payload = constants.ResourceConstants.\
                ACTIVATE_PAYLOAD_RHEL
        elif resource_type == constants.ResourceConstants.HLINUX:
            activate_payload = constants.ResourceConstants.\
                ACTIVATE_PAYLOAD_HLINUX
        elif resource_type == constants.ResourceConstants.HYPERV:
            activate_payload = constants.ResourceConstants.\
                ACTIVATE_PAYLOAD_HYPERV
        return activate_payload


class ProvisionController(rest.RestController):
    @expose(generic=True, template='json')
    def index(self):
        pass

    def _validate_body(self, res_id, data):
        self.validator = validators.ResourceValidator()
        res_type = data.get('type', None)
        self.validator.validate_type(
            res_type, constants.ResourceConstants.SUPPORTED_TYPES)
        self.validator.validate_keys_for_type(res_type, data)

    @index.when(method="POST", template='json')
    @api.handle_exceptions()
    def provision(self, resource_id):
        req = pecan.request
        data = api.load_body(req)
        self._validate_body(resource_id, data)
        LOG.debug("Provisioning begins for the resource %s " % resource_id)
        return pecan.request.rpcapi_v2.provision_resource(
            pecan.request.context, resource_id, data)
