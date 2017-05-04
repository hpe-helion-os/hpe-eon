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
import pecan

from eon.api import acl
from eon.api import config
from eon.api import hooks
from eon.api import middleware
from eon.common import policy
from eon.common import utils
from eon.openstack.common import log

LOG = log.getLogger(__name__)

auth_opts = [
    cfg.StrOpt('auth_strategy',
               default='keystone',
               help='Method to use for authentication: noauth or keystone.'),
    ]

audit_opts = [
    cfg.StrOpt('auditing',
               default='True',
               help='Enable AuditMiddleware.'),
    cfg.StrOpt('audit_map_file',
               help='API controllers mapping file for eon audit logs.'),
]
CONF = cfg.CONF
CONF.register_opts(auth_opts)
CONF.register_opts(audit_opts)


def get_pecan_config():
    # Set up the pecan configuration
    filename = config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


def setup_app(pecan_config=None, extra_hooks=None):
    policy.init()

    app_hooks = [hooks.ConfigHook(),
                 hooks.DBHook(),
                 hooks.ContextHook(pecan_config.app.acl_public_routes),
                 hooks.RPCHook(),
                 hooks.NoExceptionTracebackHook()]
    if extra_hooks:
        app_hooks.extend(extra_hooks)

    if not pecan_config:
        pecan_config = get_pecan_config()

    if pecan_config.app.enable_acl:
        app_hooks.append(hooks.AdminAuthHook())

    pecan.configuration.set_config(dict(pecan_config), overwrite=True)

    app = pecan.make_app(
        pecan_config.app.root,
        static_root=pecan_config.app.static_root,
        debug=CONF.debug,
        force_canonical=getattr(pecan_config.app, 'force_canonical', True),
        hooks=app_hooks,
        wrap_app=middleware.ParsableErrorMiddleware,
    )

    if pecan_config.app.enable_audit:
        app = acl.install_audit(app, cfg.CONF,
                                pecan_config.app.acl_public_routes)
    if pecan_config.app.enable_acl:
        app = acl.install_auth(app, cfg.CONF,
                               pecan_config.app.acl_public_routes)

    return app


class VersionSelectorApplication(object):
    def __init__(self):
        pc = get_pecan_config()
        pc.app.enable_acl = (CONF.auth_strategy == 'keystone')
        pc.app.enable_audit = (CONF.auditing == 'True')
        self.v = setup_app(pecan_config=pc)
        self.pecan_config = pc

    def __call__(self, environ, start_response):
        path = utils.safe_rstrip(environ.get('PATH_INFO'), '/')
        method = environ.get('REQUEST_METHOD')
        protocol = environ.get('SERVER_PROTOCOL')
        server = environ.get('SERVER_NAME')
        if path not in self.pecan_config.app.acl_public_routes:
            LOG.info(server + " " + method + " " + path + " " + protocol)
        return self.v(environ, start_response)
