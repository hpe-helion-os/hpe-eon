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

from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.deployer.network.ovsvapp.cleanup.cleanup import Cleanup
from eon.deployer.util import VMwareUtils


class ProxyInstallerUtility(object):
    """
    Wrapper class which consumes the ovsvapp's utilities for
    create/configure/cleanup the network infrastructures (DVS and PGs)
    """
    def __init__(self, input_json):
        self.input_json = input_json
        vc = self.input_json.get('vcenter_configuration')
        self.si = VMwareUtils.get_vcenter_session(vc['ip_address'],
                                                  vc['port'],
                                                  vc['username'],
                                                  vc['password'])
        self.content = self.si.RetrieveContent()
        self.dc = VMwareUtils.get_data_center(self.content,
                                              vc['datacenter'])
        self.vc = vc
        self.network_adapter = NetworkAdapter(self.si,
                                              self.dc['networkFolder'])

    def create_network_infrastructure(self):
        """
        Wrapper method to create the required DVS and PGs
        """
        self.network_adapter.create_dvs_portgroup(self.input_json)

    def configure_network_infrastructure(self):
        """
        Wrapper method to configure the DVS and PGs
        """
        cluster = VMwareUtils.get_cluster(self.content,
                                          self.dc['hostFolder'],
                                          self.vc['cluster_moid'])
        all_hosts = VMwareUtils.get_all_hosts(self.content, cluster)
        self.network_adapter.configure_dvs_portgroup(self.input_json,
                                                     all_hosts)

    @staticmethod
    def teardown_network(data):
        """
        Wrapper method to clean up the DVS and PGs
        """
        return Cleanup(data).teardown_network()
