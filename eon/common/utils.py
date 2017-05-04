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

import hashlib
import os
import signal
import socket as os_socket
import six
import subprocess

from oslo_config import cfg

import eon.openstack.common.log as logging
from eon.common.gettextutils import _
from eon.common import exception


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


def get_appliance_name():
    """Returns the hostname of the appliance."""
    proc = subprocess.Popen(["hostname"],
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE
                            )
    for line in proc.stdout:
        return line.split()[-1]


def timeout(timeout_time_in_sec, time_out_msg):
    def timeout_function(meth):

        def wrapper(*args, **kwargs):

            def timeout_handler(_signum, _frame):
                raise Exception(time_out_msg)

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_time_in_sec)
            try:
                retval = meth(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return wrapper
    return timeout_function


def run_command_get_output(cmd, **kwargs):
    """Runs the specified command and returns its output."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         **kwargs)
    output = p.stdout.read()
    return output


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, six.string_types):
        LOG.warn("Failed to remove trailing character. Returning original "
                 "object. Supplied object is not a string: %s," % value)
        return value

    return value.rstrip(chars) or value


class LazyPluggable(object):
    """A pluggable backend loaded lazily based on some value."""

    def __init__(self, pivot, config_group=None, **backends):
        self.__backends = backends
        self.__pivot = pivot
        self.__backend = None
        self.__config_group = config_group

    def __get_backend(self):
        if not self.__backend:
            if self.__config_group is None:
                backend_name = CONF[self.__pivot]
            else:
                backend_name = CONF[self.__config_group][self.__pivot]
            if backend_name not in self.__backends:
                msg = _('Invalid backend: %s') % backend_name
                raise exception.EonException(msg)

            backend = self.__backends[backend_name]
            if isinstance(backend, tuple):
                name = backend[0]
                fromlist = backend[1]
            else:
                name = backend
                fromlist = backend

            self.__backend = __import__(name, None, None, fromlist)
        return self.__backend


def read_cached_file(filename, cache_info, reload_func=None):
    """Read from a file if it has been modified.

    :param cache_info: dictionary to hold opaque cache.
    :param reload_func: optional function to be called with data when
                        file is reloaded due to a modification.

    :returns: data from file

    """
    mtime = os.path.getmtime(filename)
    if not cache_info or mtime != cache_info.get('mtime'):
        LOG.debug("Reloading cached file %s" % filename)
        with open(filename) as fap:
            cache_info['data'] = fap.read()
        cache_info['mtime'] = mtime
        if reload_func:
            reload_func(cache_info['data'])
    return cache_info['data']


def get_hash(data):
    """
    :param data: String to be hashed
    :return: hash value for the string passed using sha1 algorithm
    """
    return hashlib.sha1(data).hexdigest()


def get_addresses(ip_or_name):
    ipaddrlist = []
    try:
        (hostname, aliaslist, ipaddrlist) = os_socket.gethostbyaddr(
                                                            ip_or_name)
        ipaddrlist.append(hostname)
        return ipaddrlist
    except Exception as e:
        # Provided IP/FQDN is not resolvable
        LOG.info("Could not resolve %s", ip_or_name)
        LOG.info(e)
        ipaddrlist.append(ip_or_name)
    return ipaddrlist
