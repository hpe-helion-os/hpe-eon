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

import mock
import json
import webob

from eon.api.controllers.v2 import resource_actions
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
from eon.common.constants import ResourceConstants


class TestResourceAction(base_test.TestCase):

    def setUp(self):
        base_test.TestCase.setUp(self)
        self.rsrc_activate = resource_actions.ActivateController()
        self.rsrc_deactivate = resource_actions.DectivateController()
        self.rsrc_get_tempate = resource_actions.GetTemplateController()
        self.rsrc_provision = resource_actions.ProvisionController()
        resource_actions.pecan = mock.MagicMock()
        resource_actions.pecan.request = mock.MagicMock()
        self.req = resource_actions.pecan.request
        self.req.context = mock.MagicMock()
        self.context = self.req.context

    def test_activate(self):
        with mock.patch.object(self.req.rpcapi_v2,
                               'activate_resource') as activate:
            self.req.body = json.dumps(fake_data.activate_data)
            self.rsrc_activate.activate(fake_data.fake_id1)
            activate.assert_called_once_with(self.context, fake_data.fake_id1,
                                             fake_data.activate_data)

    def test_deactivate(self):
        with mock.patch.object(self.req.rpcapi_v2,
                               'deactivate_resource') as deactivate:
            self.req.body = json.dumps(fake_data.activate_data)
            self.rsrc_deactivate.deactivate(fake_data.fake_id1)
            deactivate.assert_called_once_with(self.context,
                                               fake_data.fake_id1,
                                               fake_data.activate_data)

    def test_get_info_templ_esx(self):
        with mock.patch.object(resource_actions.GetTemplateController,
                              "load_json_template_with_comments"
            ) as load_json:
            self.req.body = json.dumps({})
            load_json.return_value = {"hlm_info": {}}
            expected = ResourceConstants.ACTIVATE_PAYLOAD_ESX
            expected["network_properties"] = load_json
            expected["input_model"]["server_group"] = "RACK1"
            actual = self.rsrc_get_tempate.get_template(
                    ResourceConstants.ESXCLUSTER)
            self.assertEqual(expected, actual)
            self.assertEqual("RACK1", actual["input_model"]["server_group"])

    def test_get_info_templ_hlinux(self):
        with mock.patch.object(resource_actions.GetTemplateController,
                              "load_json_template_with_comments"
            ) as load_json:
            self.req.body = json.dumps({})
            load_json.return_value = {"hlm_info": {}}
            actual = self.rsrc_get_tempate.get_template(
                    ResourceConstants.HLINUX)
            self.assertEqual("", actual["input_model"]["server_group"])
            self.assertEqual("", actual["input_model"]["nic_mappings"])
            self.assertEqual("", actual["input_model"]["server_role"])

    def test_get_info_templ_rhel(self):
        with mock.patch.object(resource_actions.GetTemplateController,
                              "load_json_template_with_comments"
            ) as load_json:
            self.req.body = json.dumps({})
            load_json.return_value = {"hlm_info": {}}
            actual = self.rsrc_get_tempate.get_template(
                    ResourceConstants.RHEL)
            self.assertEqual("", actual["input_model"]["server_group"])
            self.assertEqual("", actual["input_model"]["nic_mappings"])
            self.assertEqual("", actual["input_model"]["server_role"])
            self.assertEqual(False, actual["run_wipe_disks"])

    def test_get_info_templ_unsupported_failure(self):
        with mock.patch.object(resource_actions.GetTemplateController,
                              "load_json_template_with_comments"
            ) as load_json:
            self.req.body = json.dumps({})
            load_json.return_value = {"hlm_info": {}}
            self.assertRaises(webob.exc.HTTPBadRequest,
                              self.rsrc_get_tempate.get_template,
                              "UNSUPPORTED")

    def test_provision_hlinux(self):
        with mock.patch.object(self.req.rpcapi_v2,
                               'provision_resource') as provision:
            self.req.body = json.dumps(fake_data.provision_data)
            self.rsrc_provision.provision(fake_data.fake_id1)
            provision.assert_called_once_with(self.context,
                                              fake_data.fake_id1,
                                              fake_data.provision_data)

    def test_provision_hlinux_failure(self):
        self.req.body = json.dumps(fake_data.provision_data_hlinux)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.rsrc_provision.provision, fake_data.fake_id1)

    def test_provision_rhel(self):
        with mock.patch.object(self.req.rpcapi_v2,
                               'provision_resource') as provision:
            self.req.body = json.dumps(fake_data.provision_data_rhel)
            self.rsrc_provision.provision(fake_data.fake_id1)
            provision.assert_called_once_with(self.context,
                                              fake_data.fake_id1,
                                              fake_data.provision_data_rhel)

