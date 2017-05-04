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
import logging.config
import logging.handlers
import os
import sys

from eon.common.gettextutils import _
from eon.common import rpc
from oslo_config import cfg
from paste import deploy

from eon.version import version_info as version

paste_deploy_opts = [
    cfg.StrOpt('flavor',
               help=(_('Partial name of a pipeline in your paste configuration'
                       ' file with the service name removed. For example, if '
                       'your paste section name is '
                       '[pipeline:isc-api-keystone] use the value '
                       '"keystone"'))),
    cfg.StrOpt('config_file',
               help=(_('Name of the paste configuration file.'))),
]
common_opts = [
    cfg.IntOpt('limit_param_default', default=25,
               help=(_('Default value for the number of items returned by a '
                       'request if not specified explicitly in the request'))),
    cfg.IntOpt('api_limit_max', default=1000,
               help=(_('Maximum permissible number of items that could be '
                       'returned by a request'))),
    cfg.StrOpt('pydev_worker_debug_host', default=None,
               help=(_('The hostname/IP of the pydev process listening for '
                       'debug connections'))),
    cfg.IntOpt('pydev_worker_debug_port', default=5678,
               help=(_('The port on which a pydev process is listening for '
                       'connections.'))),
    cfg.StrOpt('metadata_encryption_key', secret=True,
               help=(_('Key used for encrypting sensitive metadata while '
                       'talking to the registry or database.'))),
]

CONF = cfg.CONF
CONF.register_opts(paste_deploy_opts, group='paste_deploy')
CONF.register_opts(common_opts)


def parse_args(args=None, usage=None, default_config_files=None):
    rpc.set_defaults(control_exchange='eon')
    CONF(args=args,
         project='eon',
         version=version.cached_version_string(),
         usage=usage,
         default_config_files=default_config_files)
    rpc.init(cfg.CONF)


def setup_logging():
    """
    Sets up the logging options for a log with supplied name
    """

    if CONF.log_config:
        # Use a logging configuration file for all settings...
        if os.path.exists(CONF.log_config):
            logging.config.fileConfig(CONF.log_config)
            return
        else:
            raise RuntimeError(_("Unable to locate specified logging "
                                 "config file: %s" % CONF.log_config))

    root_logger = logging.root
    if CONF.debug:
        root_logger.setLevel(logging.DEBUG)
    elif CONF.verbose:
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.WARNING)

    formatter = logging.Formatter(CONF.log_format, CONF.log_date_format)

    if CONF.use_syslog:
        try:
            facility = getattr(logging.handlers.SysLogHandler,
                               CONF.syslog_log_facility)
        except AttributeError:
            raise ValueError(_("Invalid syslog facility"))

        handler = logging.handlers.SysLogHandler(address='/dev/log',
                                                 facility=facility)
    elif CONF.log_file:
        logfile = CONF.log_file
        if CONF.log-dir:
            logfile = os.path.join(CONF.log-dir, logfile)
        handler = logging.handlers.WatchedFileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def _get_paste_config_path():
    paste_suffix = '-paste.ini'
    conf_suffix = '.conf'
    if CONF.config_file:
        # Assume paste config is in a paste.ini file corresponding
        # to the last config file
        path = CONF.config_file[-1].replace(conf_suffix, paste_suffix)
    else:
        path = CONF.prog + '-paste.ini'

    return CONF.find_file(os.path.basename(path))


def get_deployment_config_file():
    """
    Retrieve the deployment_config_file config item, formatted as an
    absolute pathname.
    """
    path = CONF.paste_deploy.config_file
    if not path:
        path = _get_paste_config_path()
    if not path:
        msg = (_("Unable to locate paste config file for %s.") % CONF.prog)
        raise RuntimeError(msg)
    return os.path.abspath(path)


def load_paste_app(app_name=None):
    """
    Builds and returns a WSGI app from a paste config file.

    We assume the last config file specified in the supplied ConfigOpts
    object is the paste config file.

    :param app_name: name of the application to load

    :raises RuntimeError when config file cannot be located or application
            cannot be loaded from config file
    """
    if app_name is None:
        app_name = CONF.prog

    # append the deployment flavor to the application name,
    # in order to identify the appropriate paste pipeline

    conf_file = get_deployment_config_file()

    try:
        logger = logging.getLogger(__name__)
        logger.debug(("Loading %(app_name)s from %(conf_file)s"),
                     {'conf_file': conf_file, 'app_name': app_name})

        app = deploy.loadapp("config:%s" % conf_file, name=app_name)

        # Log the options used when starting if we're in debug mode...
        if CONF.debug:
            CONF.log_opt_values(logger, logging.DEBUG)

        return app
    except (LookupError, ImportError) as e:
        msg = (_("Unable to load %(app_name)s from "
                 "configuration file %(conf_file)s."
                 "\nGot: %(e)r") % locals())
        logger.error(msg)
        raise RuntimeError(msg)
