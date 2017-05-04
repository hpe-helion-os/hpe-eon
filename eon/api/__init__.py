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

import pecan
import json
from webob import exc
import eventlet
from oslo_config import cfg

from eon.openstack.common import log
from eon.common.constants import ResourceConstants as res_const
from eon.common import exception

from eon.openstack.common.rpc.common import Timeout as RpcTimeoutException

eventlet.monkey_patch(all=True)

API_SERVICE_OPTS = [
    cfg.StrOpt('host_ip',
               default='127.0.0.1',
               help='The listen IP for the Eon API server.'),
    cfg.IntOpt('port',
               default=8282,
               help='The port for the Eon API server.'),
    cfg.IntOpt('api_workers', default=3,
               help=_('Number of workers for Eon API service. '
                      'The default is equal to the number of CPUs available '
                      'if that can be determined, else a default worker '
                      'count of 1 is returned.')),
    cfg.IntOpt('max_limit',
               default=1000,
               help='The maximum number of items returned in a single '
                    'response from a collection resource.'),
    ]

NETWORK_OPTS = [
    cfg.StrOpt('esx_network_driver',
               default='ovsvapp',
               help='The network driver for ESX type cloud')
]
NETWORK_GROUP = cfg.OptGroup(name='network',
                             title='Option for network driver')

CONF = cfg.CONF
opt_group = cfg.OptGroup(name='api',
                         title='Options for the eon-api service')
CONF.register_group(opt_group)
CONF.register_opts(API_SERVICE_OPTS, opt_group)
CONF.register_group(NETWORK_GROUP)
CONF.register_opts(NETWORK_OPTS, NETWORK_GROUP)

LOG = log.getLogger(__name__)


def handle_exceptions():
    """Decorator handling generic exceptions from REST methods."""

    def exceptions_decorator(fn):
        def handler(inst, *args, **kwargs):
            try:
                return fn(inst, *args, **kwargs)
            except exc.HTTPError:
                LOG.exception(_('Webob error seen'))
                raise
            except exception.ResourceNotFound as e:
                LOG.exception(e.message)
                status_code = getattr(e, "status_code", 404)

            except RpcTimeoutException as e:
                LOG.exception(e)
                status_code = getattr(e, "status_code", 408)

            except (exception.InsufficientParamsError,
                    exception.InvalidIdError,
                    exception.InvalidNameError,
                    exception.InvalidUsernameError,
                    exception.InvalidPasswordError,
                    exception.InvalidIPAddressError,
                    exception.InvalidPortError,
                    exception.InvalidStateError,
                    exception.Invalid,
                    exception.ValidTemplateNotFound,
                    exception.RetrieveException) as e:
                LOG.exception(e.message)
                pecan.abort(400, e.message)

            except (exception.ActivationFailure,
                    exception.CreateException,
                    exception.DeleteException) as e:
                LOG.exception(e.message)
                pecan.abort(400, e.message)

            except exception.ResourceExists as e:
                pass

            except Exception as e:
                LOG.exception(e.message)
                status_code = getattr(e, "status_code", 500)

            pecan.abort(status_code, e.message)

        return handler

    return exceptions_decorator


def load_body(req, validator=None):
    """Helper function for loading an HTTP request body from JSON.

    :param req: The HTTP request instance to load the body from.
    :param validator: The JSON validator to enforce.
    :return: A dict of values from the JSON request.
    """
    try:
        parsed_body = json.loads(req.body)

    except (ValueError, TypeError):
        pecan.abort(400, _('Malformed JSON'))

    if validator:
        validator(parsed_body)

    return parsed_body


def load_query_params(kw, validator):
    """Helper function for loading query params
    :param kw: a dict
    :param validator: The validator method to enforce.
    :return: A dict of validated values, same as @kw
    """
    try:
        if kw:
            validator(kw)

        else:
            kw = dict()
    except Exception as e:
        LOG.exception(e.message)
        raise e
    return {k: kw.get(k) for k in res_const.API_FILTER_KEYS}
