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

import oslo_messaging as messaging

from eventlet import greenpool
from oslo_config import cfg

from eon.common import constants
from eon.virt import manager
from eon.openstack.common import log
from eon.openstack.common import periodic_task


LOG = log.getLogger(__name__)

con_mgr_opts = [
    cfg.IntOpt("poll_resource_interval",
               default=60,
               help="auto-import resource refresh period."),
]

cfg.CONF.register_opts(con_mgr_opts)
CONF = cfg.CONF

MANAGER_TOPIC = constants.CONDUCTOR_MANAGER_TOPIC


class ConductorManager(periodic_task.PeriodicTasks):
    """Eon Conductor service main class."""

    RPC_API_VERSION = '2.0'
    AUTO_IMPORT_RESOURCE_MGRS = ['vcenter']
    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, host, topic):
        super(ConductorManager, self).__init__()
        periodic_task.PeriodicTasks.__init__(self)
        self.topic = topic
        self._resource_mgr = manager.ResourceManager()
        self._resource = manager.Resource()

    def start(self):
        # GreenPool of background workers for performing tasks async
        self._worker_pool = greenpool.GreenPool(size=CONF.rpc_thread_pool_size)
        self._resource_mgr.start(self.context)

    def get_all_resource_mgrs(self, context, type_=None):
        """
        @param type_: vcenter/scvmm/oneview
        """
        eon_resource_mgr = self._resource_mgr.get_all(context, type_)
        if not eon_resource_mgr:
            return []

        return eon_resource_mgr

    def get_resource_mgr(self, context, id_, with_inventory):
        if with_inventory:
            return self._resource_mgr.get_with_inventory(context=context,
                                                         id_=id_)
        else:
            return self._resource_mgr.get(context=context, id_=id_)

    def create_resource_mgr(self, context, data):
        return self._resource_mgr.create(context=context, data=data)

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    @periodic_task.periodic_task(spacing=CONF.poll_resource_interval,
                                 run_immediately=True)
    def auto_import_resources(self, context):
        """
        This method is periodically called with the interval
        :CONF.poll_resource_interval
        :param context: admin Context
        """
        for resource_mgr_type in self.AUTO_IMPORT_RESOURCE_MGRS:
            self._worker_pool.spawn_n(self._resource_mgr.auto_import_resources,
                                      context,
                                      resource_mgr_type)

    def update_resource_mgr(self, context, id_, update_data):
        return self._resource_mgr.update(
            context=context, id_=id_, update_data=update_data)

    def delete_resource_mgr(self, context, id_):
        return self._resource_mgr.delete(context=context, id_=id_)

    def get_all_resources(self, context, filters=None):
        """
        @param filters: Dictionary with resource type and state
            {"type": "<resource type>",
             "state": "<resource state>"}
        """
        eon_resource = self._resource.get_all(context, filters=filters)
        if not eon_resource:
            return []

        return eon_resource

    def get_resource(self, context, id_, with_inventory):
        if with_inventory:
            return self._resource.get_with_inventory(context=context,
                                                     id_=id_)
        else:
            return self._resource.get(context=context, id_=id_)

    def create_resource(self, context, data):
        return self._resource.create(context=context, data=data)

    def populate_network_json(self, context, type_, data):
        return self._resource.populate_network_json(context=context,
                                                    type_=type_,
                                                    data=data)

    def activate_resource(self, context, id_, data):
        return self._resource.activate(context=context, id_=id_,
                                       data=data)

    def deactivate_resource(self, context, id_, data):
        return self._resource.deactivate(context=context, id_=id_,
                                         data=data)

    def host_commission(self, context, id_, data):
        return self._resource.host_commission(context, id_, data)

    def host_de_commission(self, context, id_, data):
        return self._resource.host_de_commission(context, id, data)

    def update_resource(self, context, id_, update_data):
        return self._resource.update(
            context=context, id_=id_, update_data=update_data)

    def delete_resource(self, context, id_):
        return self._resource.delete(context=context, id_=id_)

    def update_property(self, context, id_, rsrc_id, property_name,
                        property_value):
        return self._resource.update_property(
            context=context, id_=id_, rsrc_id=rsrc_id,
            property_name=property_name, property_value=property_value)

    def provision_resource(self, context, id_, data):
        return self._resource.provision(context=context,
                                        id_=id_,
                                        data=data)
