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

from oslo_config import cfg

from eon.openstack.common import importutils

sql_connection_opt = cfg.StrOpt('esx_sql_connection',
                                default=None,
                                secret=True,
                                metavar='CONNECTION',
                                help='A valid SQLAlchemy connection '
                                     'string for the registry database. '
                                     'Default: %(default)s')
data_api_opt = [
    cfg.StrOpt('data_api', default='eon.db.sqlalchemy.api',
               help='Python module path of data access API - current version')
]


CONF = cfg.CONF
CONF.register_opt(sql_connection_opt)
CONF.register_opts(data_api_opt)


def add_cli_options():
    """
    Adds any configuration options that the db layer might have.

    :retval None
    """
    CONF.unregister_opt(sql_connection_opt)
    CONF.register_cli_opt(sql_connection_opt)


def get_api():
    return importutils.import_module(CONF.data_api)


# attributes common to all models
BASE_MODEL_ATTRS = set(['id', 'created_at', 'updated_at', 'deleted_at',
                        'deleted'])

VCENTER_REQUIRED_ATTRS = set(['name', 'username', 'password',
                              'ip_address', 'port', 'type'])

VCENTER_ATTRS = BASE_MODEL_ATTRS | VCENTER_REQUIRED_ATTRS | set(['resources'])

ESX_PROXY_REQUIRED_ATTRS = set(['name', 'ip_address', 'routing_key',
                            'vcenter_id'])

ESX_PROXY_ATTRS = BASE_MODEL_ATTRS | ESX_PROXY_REQUIRED_ATTRS

ESX_PROXY_IPPOOL_ATTRS = set(['pool_type', 'id'])
ESX_PROXY_IP_ATTRS = set(['ipaddress', 'id'])

RESOURCE_ENTITY_REQUIRED_ATTRS = set(['name', 'path', 'vcenter_id',
                                      'resource_moid'])

RESOURCE_ENTITY_ATTRS = (BASE_MODEL_ATTRS |
                         RESOURCE_ENTITY_REQUIRED_ATTRS | set(
                         ['state', 'esx_proxy_id', 'resource_id', 'type',
                         'resource_moid', 'resource_name', 'resource_uuid']))
