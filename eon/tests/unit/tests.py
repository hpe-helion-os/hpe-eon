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

import logging

import pecan
import eventlet
import mox
import stubout
import testtools
from oslo_config import cfg

from eon import context as isc_context
from eon.common import exception
from eon.tests.unit.db.simple import api as simple_db


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

eventlet.monkey_patch(
    all=False, os=True, select=True, socket=True, thread=False, time=True)

TENANT1 = '6838eb7b-6ded-434a-882c-b344c77fe8df'

USER1 = '54492ba0-f4df-4e4e-be62-27f4d76b29cf'

CONF = cfg.CONF

APPLIANCE_HOSTNAME = "ApplianceName-proxy-0"

UUID_1 = 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d'
UUID_2 = 'a85abd86-55b3-4d5b-b0b4-5d0a6e6042fc'
UUID_3 = '971ec09a-8067-4bc8-a91f-ae3557f1c4c7'
UUID_4 = None

IPADDRESS_1 = '17.17.17.20'
IPADDRESS_2 = '17.17.17.21'
IPADDRESS_3 = '17.17.17.22'
IPADDRESS_4 = '17.17.17.23'


VCENTER_1 = 'vcenter-1'
VCENTER_2 = 'vcenter-2'
VCENTER_3 = 'vcenter-3'
VCENTER_4 = 'vcenter-4'

USERNAME_1 = 'demo'
PASSWORD_1 = 'demo'
PASSWORD_ID_1 = '1'

USERNAME_2 = 'hp'
PASSWORD_2 = 'hp'
PASSWORD_ID_2 = '2'

USERNAME_3 = 'root'
PASSWORD_3 = 'root'
PASSWORD_ID_3 = '3'

USERNAME_4 = 'admin'
PASSWORD_4 = 'admin'
PASSWORD_ID_4 = '4'

VC_PROPERTIES_UUID_1 = '88a734c2-0ef5-43dc-a5ac-a99f0adda00e'
VC_PROPERTIES_UUID_2 = 'd6573715-f3d6-4718-93b6-ac81af159f34'
VC_PROPERTIES_UUID_3 = 'bcdd727b-527b-4359-8de6-1e733e1e040d'
VC_PROPERTIES_UUID_4 = 'bcee727b-527b-ee59-8de6-1e733e1e040d'
VC_PROPERTIES_UUID_5 = 'bcff727b-527b-ff59-8de6-1e733e1e040d'

VC_PROPERTIES_NAME_1 = 'Datacenter-51'
VC_PROPERTIES_TYPE_1 = 'datacenter'
VC_PROPERTIES_VALUE_1 = 'dvSwitch-demo/dvs'

VC_PROPERTIES_NAME_2 = 'pulsar01_compute_CL2'
VC_PROPERTIES_NAME_3 = 'pulsar01_compute_CL3'

VC_PROPERTIES_TYPE_2 = 'cluster'

VC_PROPERTIES_VALUE_2 = '{resource_moid: "domain-c1731",\
                               "state": "imported", \
                               "resource_name": "pulsar01_compute_CL2"} '

VC_PROPERTIES_NAME_4 = 'pulsar01_compute_CL1'
VC_PROPERTIES_TYPE_4 = 'cluster'
VC_PROPERTIES_VALUE_4 = '{resource_moid: "domain-c1732",\
                               "state": "imported", \
                               "resource_name": "pulsar01_compute_CL1"} '
VC_PROPERTIES_NAME_5 = 'vshield_password'
VC_PROPERTIES_TYPE_5 = 'credential'
VC_PROPERTIES_VALUE_5 = 'password'

RESOURCE_ID_1 = '22a734c2-02f5-43dc-a5ac-a29f0adda00e'
RESOURCE_ID_2 = '33a734c2-02f5-42dc-a8ac-a29f0adda00e'

RESOURCE_NAME_1 = 'pulsar01_compute_CL1'
RESOURCE_NAME_2 = 'pulsar01_compute_CL2'
RESOURCE_NAME_3 = 'pulsar01_compute_CL3'

RESOURCE_PATH_1 = 'Datacenter/host/pulsar01_compute_CL1:pulsar01-CL1-vds'
RESOURCE_PATH_2 = 'Datacenter/host/pulsar01_compute_CL2:pulsar01-CL2-vds'


RESOURCE_STATE_1 = 'not_imported'
RESOURCE_STATE_2 = 'imported'
RESOURCE_STATE_3 = 'error'
RESOURCE_STATE_4 = 'active'

RESOURCE_MOID_1 = 'domain-c1731'

# data for imported state
RESOURCE_DATA_1 = {
                 "resource_name": VC_PROPERTIES_NAME_2,
                 "resource_moid": RESOURCE_MOID_1,
                 "vcenter_id": UUID_1
                 }
# data for not_imported state
RESOURCE_DATA_2 = {
                 "resource_name": VC_PROPERTIES_NAME_3,
                 "resource_moid": RESOURCE_MOID_1,
                 "vcenter_id": UUID_1
                 }

ESX_PROXY_ID_1 = '1731b319-9ddd-4dd8-aad5-cadaa39ed73e'

DATACENTER_NAME_1 = 'Datacenter_1'

RESOURCE_ENTITY_DATA_1 = {
                          'name': VC_PROPERTIES_NAME_2,
                          'type': VC_PROPERTIES_TYPE_2,
                          'path': RESOURCE_PATH_1,
                          'vcenter_id': UUID_1,
                          'esx_proxy_id': ESX_PROXY_ID_1,
                          'state': 'active',
                          }

RESOURCE_ENTITY_DATA_2 = {
                          'name': VC_PROPERTIES_NAME_2,
                          'resource_name': VC_PROPERTIES_NAME_2,
                          'type': VC_PROPERTIES_TYPE_2,
                          'path': RESOURCE_PATH_1,
                          'vcenter_id': UUID_1,
                          'esx_proxy_id': ESX_PROXY_ID_1,
                          'state': 'active',
                          }

VSHEILD_DATA_1 = {'vshield_username': 'username',
                  'vshield_password': 'password',
                  'vshield_ip_address': '10.10.10.10'}

CLUSTER_DATA = {'inventory': {'datacenter-184': {'clusters': [{'hosts':
                    {'host-297': {'switches':
                        {'key-vim.host.VirtualSwitch-vSwitch3':
                         {'name': 'vSwitch3', 'type': 'std_switch'}},
                                  'connection_state': 'connected'}}}]}}}

PROXY_DATA = {'id': ESX_PROXY_ID_1,
              'vcenter_id': UUID_1,
              'hostname': APPLIANCE_HOSTNAME,
              'routing_key': APPLIANCE_HOSTNAME,
              'name': APPLIANCE_HOSTNAME
              }

RESPONSE_1 = {'resource_entity_meta': {
                 "resource_name": VC_PROPERTIES_NAME_3,
                 "resource_moid": RESOURCE_MOID_1,
                 "vcenter_id": UUID_1
                 }}


class BaseTestCase(testtools.TestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.mox = mox.Mox()
        self.addCleanup(CONF.reset)
        self.stubs = stubout.StubOutForTesting()
        self.stubs.Set(exception, '_FATAL_EXCEPTION_FORMAT_ERRORS', True)

    def tearDown(self):
        self.mox.UnsetStubs()
        self.stubs.UnsetAll()
        self.stubs.SmartUnsetAll()
        super(BaseTestCase, self).tearDown()

    def config(self, **kw):
        """
        Override some configuration values.

        The keyword arguments are the names of configuration options to
        override and their values.

        If a group argument is supplied, the overrides are applied to
        the specified configuration option group.

        All overrides are automatically cleared at the end of the current
        test by the fixtures cleanup process.
        """
        group = kw.pop('group', None)
        for k, v in kw.iteritems():
                        CONF.set_override(k, v, group)

    def fake_vcenter(self):
        return {'ip_address': '10.10.10.10',
                'username': 'vcenter-1',
                'password': 'password'
                }

    def fake_esx_proxy(self):
        return {'hostname': 'isc', 'routing_key': 'isc', 'id': 1}

    def fake_resource(self):
        return {'resource_name': 'cluster-1',
                'hostname': 'esx-host',
                'cluster_dvs_path': 'Datacente/host/cluster-1:dvswitch'}


class BaseControllerTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

    def _vCenter_db_fixture(self, id, **kwargs):
        obj = {
               'id': id,
               'name': None,
               'ip_address': None,
               'username': None,
               'password': 'password',
               'password_id': None,
               'status': None
               }
        obj.update(kwargs)
        return obj

    def _vCenter_create_db_entries(self):
        """Create all database records needed for unit test."""
#         self.db.reset()

        self.vcenters = [
             self._vCenter_db_fixture(UUID_1, name=VCENTER_1,
                                      ip_address=IPADDRESS_1,
                                      username=USERNAME_1,
                                      password=PASSWORD_1,
                                      password_id=PASSWORD_ID_1),
             self._vCenter_db_fixture(UUID_2, name=VCENTER_2,
                                      ip_address=IPADDRESS_2,
                                      username=USERNAME_2,
                                      password=PASSWORD_2,
                                      password_id=PASSWORD_ID_2),
            self._vCenter_db_fixture(UUID_3, name=VCENTER_3,
                                     ip_address=IPADDRESS_3,
                                     username=USERNAME_3,
                                     password=PASSWORD_3,
                                     password_id=PASSWORD_ID_3)
              ]
        [self.db.vcenter_create(None, vcenter) for vcenter in self.vcenters]

    def _vCenter_properties_db_fixture(self, id, **kwargs):
        obj = {
               'id': id,
               'resource_id': None,
               'name': None,
               'type': None,
               'value': None
               }
        obj.update(kwargs)
        return obj

    def _vCenter_properties_create_db_entries(self):
        """Create all database records needed for unit test."""
        self.vcenter_properties = [
             self._vCenter_properties_db_fixture(VC_PROPERTIES_UUID_1,
                                                 resource_id=UUID_1,
                                                 name=VC_PROPERTIES_NAME_1,
                                                 type=VC_PROPERTIES_TYPE_1,
                                                 value=VC_PROPERTIES_VALUE_1),
             self._vCenter_properties_db_fixture(VC_PROPERTIES_UUID_2,
                                                 resource_id=UUID_1,
                                                 name=VC_PROPERTIES_NAME_2,
                                                 type=VC_PROPERTIES_TYPE_2,
                                                 value=VC_PROPERTIES_VALUE_2),
             self._vCenter_properties_db_fixture(VC_PROPERTIES_UUID_4,
                                                 resource_id=UUID_1,
                                                 name=VC_PROPERTIES_NAME_4,
                                                 type=VC_PROPERTIES_TYPE_4,
                                                 value=VC_PROPERTIES_VALUE_4),
            self._vCenter_properties_db_fixture(VC_PROPERTIES_UUID_5,
                                                 resource_id=UUID_1,
                                                 name=VC_PROPERTIES_NAME_5,
                                                 type=VC_PROPERTIES_TYPE_5,
                                                 value=VC_PROPERTIES_VALUE_5)
              ]
        for vcenter_property in self.vcenter_properties:
            vcenter_property = {vcenter_property['name']:
                {'prop_type': vcenter_property['type'],
                 'value': vcenter_property['value']}}
            self.db.update_resource_properties(None, UUID_1, vcenter_property)

    def _resource_entity_db_fixture(self, id, **kwargs):
        obj = {
               'id': id,
               'name': None,
               'type': None,
               'path': None,
               'vcenter_id': None,
               'esx_proxy_id': None,
               'state': None,
               }
        obj.update(kwargs)
        return obj

    def _resource_entity_create_db_entries(self):
        """Create all database records needed for unit test."""
        self.resource_entities = [
             self._resource_entity_db_fixture(RESOURCE_ID_1,
                                              name=RESOURCE_NAME_1,
                                              type=VC_PROPERTIES_TYPE_1,
                                              path=RESOURCE_PATH_1,
                                              vcenter_id=UUID_1,
                                              esx_proxy_id=ESX_PROXY_ID_1,
                                              state='starting')
                                  ]
        for resource_entity in self.resource_entities:
            self.db.resource_entity_update(None, resource_entity)


class FakeDB(object):
    def __init__(self):
        self.reset()

    @staticmethod
    def reset():
        simple_db.reset()

    def __getattr__(self, key):
        return getattr(simple_db, key)


def get_fake_request(path='', method='POST', is_admin=False, user=USER1,
                     roles=['member'], tenant=TENANT1):
    req = pecan.request
    req.method = method

    kwargs = {'user': user,
              'tenant': tenant,
              'roles': roles,
              'is_admin': is_admin,
              }

    req.context = isc_context.RequestContext(**kwargs)
    req.headers['auth'] = 'x'
    return req
