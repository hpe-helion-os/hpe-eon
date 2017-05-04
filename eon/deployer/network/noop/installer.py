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

from eon.deployer import basedriver
from oslo_config import cfg

CONF = cfg.CONF


class NoOpInstaller(basedriver.BaseDriver):
    """
    Base class for NoOp installer
    """
    def __init__(self):
        super(NoOpInstaller, self).__init__()

    def setup_network(self, data):
        pass

    def create(self, data):
        cluster_name = data.get("vcenter_configuration").get("cluster")
        return {cluster_name: None}

    def get_info(self, data):
        pass

    def delete(self, data):
        pass

    def update(self, data):
        pass

    def teardown_network(self, data):
        pass
