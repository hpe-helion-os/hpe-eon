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

import eventlet
from oslo_config import cfg

eventlet.monkey_patch(all=True)

NOVA_NEUTRON_OPTS = [
    cfg.StrOpt('admin_username',
               default='service',
               help='Username for authentication'),
    cfg.StrOpt('admin_password',
               default='service_password',
               help='Password for authentication',
               secret=True),
    cfg.StrOpt('admin_tenant_name',
               default='services',
               help='Tenant name'),
    cfg.StrOpt('admin_auth_url',
               default='http://localhost:35357/v2.0',
               help='Keystone service endpoint for authorization'),
    cfg.StrOpt('url',
               default='http://localhost:9068/v2.0',
               help='A user-supplied endpoint URL for the service'),
    cfg.StrOpt('endpoint_type',
               default='internalURL',
               help='Service endpoint type to pull from the keystone catalog'),
    cfg.IntOpt('timeout',
               default=300,
               help='Allows customization of the timeout for client http'
                    ' requests'),
    cfg.StrOpt('auth_strategy',
               default='keystone',
               help='Authentication strategy'),
    cfg.StrOpt('ca_certificates_file',
               default='/etc/ssl/certs/ca-certificates.crt',
               help='Certificate file location')
]

NETWORK_OPTS = [
    cfg.StrOpt('esx_network_driver',
               default='ovsvapp',
               help='The network driver for ESX type cloud')
]

VMWARE_TEMPLATE_OPTS = [
    cfg.StrOpt('template_location',
               default="",
               )]

VC_VERSION_OPTS = [
    cfg.ListOpt('vc_supported_version',
                default=["5.1:799731", "5.5:1476327"],
                help=(_('Supported vCenter versions and build numbers'))),
        ]

LIFECYCLE_MANAGER_OPTS = [
    cfg.StrOpt('hlm_version',
               help='The version of the lifecycle manager. Ex: "hlm-4.0.0"'),
    cfg.StrOpt('ip_address',
               default='localhost',
               help='The CONF IP of the lifecycle manager'),
    cfg.StrOpt('user',
               help='The username of the lifecycle manager'),
    cfg.StrOpt('ssh_key',
               help='The public key of the lifecycle manager'),
]

CONF = cfg.CONF
NEUTRON_GROUP = cfg.OptGroup(name='neutron',
                             title='Options for the neutron service')
NOVA_GROUP = cfg.OptGroup(name='nova',
                          title='Options for the nova service')
NETWORK_GROUP = cfg.OptGroup(name='network',
                             title='Option for ESX network driver')
VMWARE_GROUP = cfg.OptGroup(name='vmware',
                            title='Option for hLinux VM template location')
LIFECYCLE_MANAGER_GRP = cfg.OptGroup(name='lifecycle_manager',
                                     title='Options for lifecycle manger info')

CONF.register_group(NEUTRON_GROUP)
CONF.register_group(NOVA_GROUP)
CONF.register_opts(NOVA_NEUTRON_OPTS, NEUTRON_GROUP)
CONF.register_opts(NOVA_NEUTRON_OPTS, NOVA_GROUP)

CONF.register_group(NETWORK_GROUP)
CONF.register_opts(NETWORK_OPTS, NETWORK_GROUP)
CONF.register_opts(VC_VERSION_OPTS)
CONF.register_opts(VMWARE_TEMPLATE_OPTS, VMWARE_GROUP)
CONF.register_group(LIFECYCLE_MANAGER_GRP)
CONF.register_opts(LIFECYCLE_MANAGER_OPTS, LIFECYCLE_MANAGER_GRP)
