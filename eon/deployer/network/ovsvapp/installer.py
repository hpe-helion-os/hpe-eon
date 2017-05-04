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

from eon.deployer import basedriver
from eon.deployer.network.ovsvapp.cleanup.cleanup import Cleanup
from eon.deployer.network.ovsvapp.install import move_host
from eon.deployer.network.ovsvapp.install.ovsvapp_installer_utility import (
    OVSvAppInstallerUtility)
from oslo_config import cfg

CONF = cfg.CONF


class OvsvappInstaller(basedriver.BaseDriver):
    """
    Base class for ovsvapp drivers
    """
    def __init__(self):
        super(OvsvappInstaller, self).__init__()

    def create(self, data):
        payload = self._ovsvapp_input(data)
        output_json = (OVSvAppInstallerUtility(payload).
                       invoke_ovsvapp_installer())
        return output_json

    def get_info(self, data):
        pass

    def delete(self, data):
        payload = self._ovsvapp_input(data)
        output_json = Cleanup(payload).unimport_cluster()
        return output_json

    def update(self, data):
        move_host.move_host_back_to_cluster(data)

    def setup_network(self, data):
        """
        Create required DVS and Portgroup for the Datacenter without any
        uplinks before Cluster Import
        :param data:
        :return: True is success else False
        """
        payload = self._ovsvapp_input(data)
        return OVSvAppInstallerUtility(payload).setup_network()

    def teardown_network(self, data):
        """
        Delete the DVS and Portgroup for the Datacenter after Cluster UnImport
        :param data:
        :return: True is success else False
        """
        payload = self._ovsvapp_input(data)
        return Cleanup(payload).teardown_network()

    def _ovsvapp_input(self, data):
        """
        Frames the data as required for ovsvapp installer
        :param data:
        :return:
        """
        neutron = dict()
        neutron['admin_username'] = CONF.neutron.admin_username
        neutron['admin_password'] = CONF.neutron.admin_password
        neutron['admin_tenant_name'] = CONF.neutron.admin_tenant_name
        neutron['admin_auth_url'] = CONF.neutron.admin_auth_url
        neutron['endpoint_url'] = CONF.neutron.url
        neutron['endpoint_type'] = CONF.neutron.endpoint_type
        neutron['timeout'] = CONF.neutron.timeout
        data.update({'neutron': neutron})
        return data
