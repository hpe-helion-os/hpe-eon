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
from oslo_config import cfg

from eon.common import constants
from eon.common import exception as exc
from eon.common import rpc
from eon.objects import base as object_base
from eon.openstack.common.rpc import common as rpc_common


# NOTE(max_lobur): This is temporary override for Oslo setting defined in
# eon.openstack.common.rpc.__init__.py. Should stay while Oslo is not fixed.
# *The setting shows what exceptions can be deserialized from RPC response.
# *This won't be reflected in eon.conf.sample
# described in https://bugs.launchpad.net/eon/+bug/1252824
cfg.CONF.set_default('allowed_rpc_exception_modules',
                     ['eon.common.exception',
                      'exceptions', ])


def check_rpc_exception(rpc_call):
    def check(*args, **kwargs):
        try:
            return rpc_call(*args, **kwargs)
        except rpc_common.RemoteError as e:
            raise exc.EonException(e.value)
    return check


class ConductorAPI(object):

    # This must be in sync with manager.ConductorManager
    RPC_API_VERSION = '2.0'

    def __init__(self, topic=None):
        super(ConductorAPI, self).__init__()
        self.topic = topic
        if topic is None:
            self.topic = constants.CONDUCTOR_MANAGER_TOPIC

        target = messaging.Target(topic=self.topic,
                                  version=self.RPC_API_VERSION)
        serializer = object_base.EonObjectSerializer()
        self.client = rpc.get_client(target, version_cap=self.RPC_API_VERSION,
                                     serializer=serializer)

    def get_all_resource_mgrs(self, context, type_):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'get_all_resource_mgrs', type_=type_)

    def get_resource_mgr(self, context, id_, with_inventory=True):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'get_resource_mgr',
                          id_=id_, with_inventory=with_inventory)

    def create_resource_mgr(self, context, data):
        cctxt = self.client.prepare(topic=self.topic, timeout=300)
        return cctxt.call(context, 'create_resource_mgr', data=data)

    def update_resource_mgr(self, context, id_, update_data):
        cctxt = self.client.prepare(topic=self.topic, timeout=120)
        return cctxt.call(context, 'update_resource_mgr',
                          id_=id_, update_data=update_data)

    def delete_resource_mgr(self, context, id_):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'delete_resource_mgr', id_=id_)

    def get_all_resources(self, context, filters):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'get_all_resources', filters=filters)

    def get_resource(self, context, id_, with_inventory=True):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'get_resource',
                          id_=id_, with_inventory=with_inventory)

    def create_resource(self, context, data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'create_resource', data=data)

    def populate_network_json(self, context, type_, data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'populate_network_json', type_=type_,
                          data=data)

    def activate_resource(self, context, id_, data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'activate_resource', id_=id_, data=data)

    def update_resource(self, context, id_, update_data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'update_resource',
                          id_=id_, update_data=update_data)

    def deactivate_resource(self, context, id_, data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'deactivate_resource', id_=id_, data=data)

    def host_commission(self, context, id_, data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'host_commission', id_=id_, data=data)

    def host_decommission(self, context, id_, data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'host_de_commission', id_=id_, data=data)

    def delete_resource(self, context, id_):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'delete_resource', id_=id_)

    def update_property(self, context, id_, rsrc_id, property_name,
                        property_value):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'update_property', id_=id_, rsrc_id=rsrc_id,
                          property_name=property_name,
                          property_value=property_value)

    def provision_resource(self, context, id_, data):
        cctxt = self.client.prepare(topic=self.topic)
        return cctxt.call(context, 'provision_resource', id_=id_, data=data)
