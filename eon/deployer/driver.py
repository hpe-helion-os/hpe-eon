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

from oslo_config import cfg

from eon.openstack.common import importutils
from eon.virt import constants

CONF = cfg.CONF


class DeployerDriver(object):
    """
    Base driver for provisioning compute
    and network proxis for hypervisors
    """
    def __init__(self):
        self._create_node = True

    def setup_network(self, data):
        raise NotImplementedError()

    def create(self, data):
        raise NotImplementedError()

    def get_info(self, data):
        raise NotImplementedError()

    def delete(self, data):
        raise NotImplementedError()

    def update(self, data):
        raise NotImplementedError()

    def teardown_network(self, data):
        raise NotImplementedError()


PROVISION_DRIVERS = {
            constants.EON_RESOURCE_TYPE_ESX_CLUSTER_NETWORK:
                "eon.deployer.network." + CONF.network.esx_network_driver +
                ".driver",
            constants.EON_RESOURCE_TYPE_ESX_CLUSTER_COMPUTE:
                "eon.deployer.computeproxy.driver"
            }


def load_resource_network_driver(resource_type_):
    """Get appropriate network driver based on resource type

    Based on the @type_ return the appropriate driver.
    :param resource_type_: type of the resource.
    """
    global PROVISION_DRIVERS
    resource_type_ = resource_type_ + "_" + "network"
    return importutils.import_class(PROVISION_DRIVERS[resource_type_])()


def load_resource_compute_driver(resource_type_):
    """Get appropriate compute driver based on resource type

    Based on the @type_ return the appropriate driver.
    :param resource_type_: type of the resource.
    """
    global PROVISION_DRIVERS
    resource_type_ = resource_type_ + "_" + "compute"
    return importutils.import_class(PROVISION_DRIVERS[resource_type_])()
