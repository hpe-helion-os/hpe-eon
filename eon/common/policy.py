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

import os.path

from oslo_config import cfg

from eon.common import utils
from eon.openstack.common import policy

CONF = cfg.CONF

_POLICY_PATH = None
_POLICY_CACHE = {}
_enforcer = None


def reset():
    global _POLICY_PATH
    global _POLICY_CACHE
    global _enforcer
    _POLICY_PATH = None
    _POLICY_CACHE = {}
    _enforcer.clear()


def init():
    global _POLICY_PATH
    global _POLICY_CACHE
    global _enforcer
    if not _POLICY_PATH:
        _POLICY_PATH = CONF.policy_file
        if not os.path.exists(_POLICY_PATH):
            _POLICY_PATH = CONF.find_file(_POLICY_PATH)
        if not _POLICY_PATH:
            raise Exception(path=CONF.policy_file)
    _enforcer = policy.Enforcer()
    utils.read_cached_file(_POLICY_PATH, _POLICY_CACHE,
                           reload_func=_set_rules)


def _set_rules(data):
    default_rule = CONF.policy_default_rule
    _enforcer.set_rules(policy.Rules.load_json(data, default_rule))


def check(rule, target, creds, exc=None, *args, **kwargs):
    return _enforcer.enforce(rule, target, creds, exc=exc, *args, **kwargs)
