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

import signal
import socket
import eventlet

eventlet.monkey_patch(all=True)

import oslo_messaging as messaging

from oslo_config import cfg
from oslo_service import service
from oslo_service import wsgi
from oslo_concurrency import processutils
from oslo_utils import importutils

from eon.api import app
from eon.common import config
from eon.common import rpc
from eon.common import context
from eon.openstack.common import log
from eon.objects import base as object_base


service_opts = [
    cfg.IntOpt('periodic_interval',
               default=60,
               help='Seconds between running periodic tasks.'),
    cfg.StrOpt('host',
               default=socket.getfqdn(),
               help='Name of this node.  This can be an opaque identifier.  '
               'It is not necessarily a hostname, FQDN, or IP address. '
               'However, the node name must be valid within '
               'an AMQP key, and if using ZeroMQ, a valid '
               'hostname, FQDN, or IP address.'),
]

visdk_opts = [
    cfg.BoolOpt('vmware_cert_check',
                default=False,
                help='Enable SSL certificate check for vCenter'),
    cfg.StrOpt('vmware_cert_path',
               default='/var/cache/eon/data/certdata/baseappliance.crt',
               help='Appliance certificate chain path containing cacert'),
]

network_opts = [
    cfg.StrOpt('network_driver',
               default='ovsvapp',
               help='The network driver for ESX type cloud')
]

keystone_opts = [
    cfg.StrOpt('endpoint_type',
               default='internalURL',
               help='keystone endpoint type'),
    cfg.StrOpt('ca_certificates_file',
               default='/etc/ssl/certs/ca-certificates.crt',
               help='SSL cacert file location'),
]
CONF = cfg.CONF
CONF.register_opts(service_opts)
CONF.register_opts(visdk_opts)
CONF.register_opts(keystone_opts, group='keystone_authtoken')

LOG = log.getLogger(__name__)


class RPCService(service.Service):

    def __init__(self, host, manager_module, manager_class):
        super(RPCService, self).__init__()
        self.host = host
        manager_module = importutils.try_import(manager_module)
        manager_class = getattr(manager_module, manager_class)
        self.manager = manager_class(host, manager_module.MANAGER_TOPIC)
        self.topic = self.manager.topic
        self.rpcserver = None
        self.deregister = True

    def start(self):
        super(RPCService, self).start()
        admin_context = context.RequestContext('admin', 'admin', is_admin=True)
        self.manager.context = admin_context
        self.manager.start()

        target = messaging.Target(topic=self.topic, server=self.host)
        endpoints = [self.manager]
        serializer = object_base.EonObjectSerializer()
        self.rpcserver = rpc.get_server(target, endpoints, serializer)
        self.rpcserver.start()
        self.handle_signal()

        self.tg.add_dynamic_timer(
            self.manager.periodic_tasks,
            periodic_interval_max=CONF.periodic_interval,
            context=admin_context)

        LOG.info(('Created RPC server for service %(service)s on host'
                  ' %(host)s.'), {'service': self.topic, 'host': self.host})

    def stop(self):
        try:
            self.rpcserver.stop()
            self.rpcserver.wait()
        except Exception as e:
            LOG.exception(('Service error occurred when stopping the '
                           'RPC server. Error: %s'), e)

        super(RPCService, self).stop(graceful=True)
        LOG.info(('Stopped RPC server for service %(service)s on host'
                  ' %(host)s.'), {'service': self.topic, 'host': self.host})

    def _handle_signal(self, signo, frame):
        LOG.info(('Got signal SIGUSR1. Not deregistering on next shutdown '
                  'of service %(service)s on host %(host)s.'),
                 {'service': self.topic, 'host': self.host})
        self.deregister = False

    def handle_signal(self):
        """Add a signal handler for SIGUSR1.

        The handler ensures that the manager is not deregistered when it is
        shutdown.
        """
        signal.signal(signal.SIGUSR1, self._handle_signal)


def process_launcher():
    return service.ProcessLauncher(CONF)


class WSGIService(service.ServiceBase):
    """Provides ability to launch EON API from wsgi app."""

    def __init__(self, name, use_ssl=False):
        """Initialize, but do not start the WSGI server.

        :param name: The name of the WSGI server given to the loader.
        :param use_ssl: Wraps the socket in an SSL context if True.
        :returns: None
        """
        self.name = name
        self.app = app.VersionSelectorApplication()
        self.workers = (CONF.api.api_workers or
                        processutils.get_worker_count())
        if self.workers and self.workers < 1:
            raise Exception(
                _("api_workers value of %d is invalid, "
                  "must be greater than 0.") % self.workers)

        self.server = wsgi.Server(CONF, name, self.app,
                                  host=CONF.api.host_ip,
                                  port=CONF.api.port,
                                  use_ssl=use_ssl)

    def start(self):
        """Start serving this service using loaded configuration.
        :returns: None
        """
        self.server.start()

    def stop(self):
        """Stop serving this API.
        :returns: None
        """
        self.server.stop()

    def wait(self):
        """Wait for the service to stop serving this API.

        :returns: None
        """
        self.server.wait()

    def reset(self):
        """Reset server greenpool size to default.

        :returns: None
        """
        self.server.reset()


def prepare_service(argv=[]):
    config.parse_args(
        default_config_files=cfg.find_config_files(project='eon'))
    cfg.set_defaults(log.log_opts,
                     default_log_levels=['amqplib=WARN',
                                         'qpid.messaging=INFO',
                                         'sqlalchemy=WARN',
                                         'keystoneclient=INFO',
                                         'stevedore=INFO',
                                         'eventlet.wsgi.server=WARN',
                                         'iso8601=WARN'
                                         ])
    cfg.CONF(argv[1:], project='eon')
    log.setup('eon')
