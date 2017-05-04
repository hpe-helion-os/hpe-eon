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

from eon.openstack.common import importutils
from eon.virt import constants

RESOURCE_MGR_DRIVERS = {constants.EON_RESOURCE_MGR_TYPE_VCENTER:
                        "eon.virt.vmware.driver.VMwareVCDriver"}

RESOURCE__DRIVERS = {
            constants.EON_RESOURCE_TYPE_ESX_CLUSTER:
                "eon.virt.vmware.driver.VMwareVCDriver",
            constants.EON_RESOURCE_TYPE_BAREMETAL:
                "eon.virt.baremetal.driver.BaremetalDriver",
            constants.EON_RESOURCE_TYPE_HLINUX:
                "eon.virt.kvm.driver.KVMDriver",
            constants.EON_RESOURCE_TYPE_RHEL:
                "eon.virt.rhel.driver.RHELDriver",
            constants.EON_RESOURCE_TYPE_HYPERV:
                "eon.virt.hyperv.driver.HyperVDriver"
            }


class ResourceDriver(object):
    """
        Base class defining interface for all resource_mgr/ resource drivers
    """

    def validate_create(self, context, create_data):
        """
           Validates the resource_mgr/ resource to be created
        """
        raise NotImplementedError()

    def monitor_events(self, resource_data):
        """
           Monitor for resource_mgr/ resource events
        """
        pass

    def validate_update(self, context, db_resource_data, update_data):
        """
           Validates the resource_mgr/ resource to be updated
        """
        raise NotImplementedError()

    def update(self, context, *args, **kwargs):
        """
            Updates the resource_mgr/ resource
        """
        pass

    def validate_delete(self, data):
        """
           Validates the resource_mgr/ resource to be deleted
        """
        pass

    def get_resource_property(self, res_prop_objs, key):
        """
        :param res_prop_objs: a list of prop table objects
        """
        for prop_obj in res_prop_objs:
            if prop_obj.key == key:
                return prop_obj.value

    def get_properties(self, create_data):
        """
           Returns the resource_mgr/ resource properties
        """
        return {}

    def populate_network_json(self, context, data):
        raise NotImplementedError()

    def auto_import_resources(self, context, db_resource_mgr_data,
                              db_rsrcs,
                              db_rsrcs_properties):
        """
           Returns list of resources added/removed
        """
        raise NotImplementedError()

    def get_inventory(self):
        """
           Returns the resource_mgr/ resource inventory on creation
        """
        raise NotImplementedError()

    def get_res_inventory(self):
        """
        Returns the resource inventory
        """
        pass

    def provision(self, context, resource_type, data,
                  network_prop):
        """
           Provisions the compute resources
        """
        pass

    def pre_activation_steps(self, context, **kwargs):
        pass

    def activate(self, context, id_, activate_data, **kwargs):
        raise NotImplementedError()

    def post_activation_steps(self, context, id_, **kwargs):
        pass

    def post_deactivation_steps(self, context, **kwargs):
        pass

    def pre_deactivation_steps(self, context, **kwargs):
        pass

    def deactivate(self, context, id_, **kwargs):
        raise NotImplementedError()

    def delete(self, context, id_, **kwargs):
        """
        For deleting the resource.
        """
        pass


def load_resource_mgr_driver(resource_mgr_type_):
    """Get appropriate driver for Create/Update/Delete operations.
     Based on the @resource_mgr_type_ return the appropriate driver.
     :param resource_mgr_type_: type of the resource_mgr.
    """
    global RESOURCE_MGR_DRIVERS
    return importutils.import_class(
        RESOURCE_MGR_DRIVERS[resource_mgr_type_])()


def load_resource_driver(resource_type_):
    """Get appropriate driver for Create/Update/Delete operations.

    Based on the @type_ return the appropriate driver.
    :param resource_type_: type of the resource.
    """
    global RESOURCE__DRIVERS
    return importutils.import_class(RESOURCE__DRIVERS[resource_type_])()
