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

from eon.hlm_facade import exception

COMMIT_MESSAGE = "[%s]: EON commit - %s"

# hlm facade endpoints
FACADE_BASE_URL = "/api/v1/hlm"
MODEL = "/model"

INPUT_MODEL_URL = FACADE_BASE_URL + MODEL
EXPANDED_INPUT_MODEL_URL = INPUT_MODEL_URL + "/expanded"
SERVERS_URL = FACADE_BASE_URL + MODEL + "/entities/servers"
INTERFACES_URL = FACADE_BASE_URL + MODEL + "/entities/interface-models"
CONTROLPLANES_URL = FACADE_BASE_URL + MODEL + "/entities/control-planes"
NETWORKS_URL = FACADE_BASE_URL + MODEL + "/entities/networks"
NETWORKS_GROUPS_URL = FACADE_BASE_URL + MODEL + "/entities/network-groups"
SERVER_GROUPS_URL = FACADE_BASE_URL + MODEL + "/entities/server-groups"
INTERFACES_URL = FACADE_BASE_URL + MODEL + "/entities/interface-models"
PASS_THROUGH_URL = FACADE_BASE_URL + MODEL + "/entities/pass-through"
EXPANDED_INPUT_MODEL_SERVERS = EXPANDED_INPUT_MODEL_URL + "/servers"
COMMIT_URL = FACADE_BASE_URL + MODEL + "/commit"
REVERT_URL = FACADE_BASE_URL + MODEL + "/changes"
CP_OUTPUT_SERVER_INFO = FACADE_BASE_URL + MODEL + "/cp_output/server_info_yml"

PLAYBOOKS = "/playbooks"
HLM_PLAYBOOKS = FACADE_BASE_URL + PLAYBOOKS
CONFIG_PROCESSOR_RUN = HLM_PLAYBOOKS + "/config_processor_run"
READY_DEPLOYMENT = HLM_PLAYBOOKS + "/ready_deployment"
SITE = HLM_PLAYBOOKS + "/site"
HLM_START = HLM_PLAYBOOKS + "/hlm_start"
HLM_STOP = HLM_PLAYBOOKS + "/hlm_stop"
HLM_STATUS = HLM_PLAYBOOKS + "/hlm_status"

PLAYS = FACADE_BASE_URL + "/plays"

PLAYBOOK_MAP = {'site': HLM_PLAYBOOKS + '/site',
                'hlm_start': HLM_PLAYBOOKS + '/hlm_start',
                'hlm_stop': HLM_PLAYBOOKS + '/hlm_stop',
                'hlm_status': HLM_PLAYBOOKS + '/hlm_status',
                'hlm_ssh_configure':
                    HLM_PLAYBOOKS + '/hlm_ssh_configure',
                'hlm_post_deactivation':
                    HLM_PLAYBOOKS + '/hlm_post_deactivation',
                'hlm_remove_cobbler_node':
                    HLM_PLAYBOOKS + '/hlm_remove_cobbler_node',
                'osconfig': HLM_PLAYBOOKS + '/osconfig_run',
                'guard_deployment': HLM_PLAYBOOKS + '/guard_deployment',
                'wipe_disks': HLM_PLAYBOOKS + '/wipe_disks',
                'hlm_deploy': HLM_PLAYBOOKS + '/hlm_deploy',
                'monasca-deploy': HLM_PLAYBOOKS + '/monasca-deploy',
                'neutron-reconfigure': HLM_PLAYBOOKS + '/neutron-reconfigure',
                'nova-reconfigure': HLM_PLAYBOOKS + '/nova-reconfigure'}

OSINSTALL = FACADE_BASE_URL + "/osinstall"

# API retry constants
RETRY_COUNT = 70
MAX_INTERVAL = 60
ESX_TIMEOUT_PER_HOST = 900
HANDLED_EXCEPTIONS = [exception.GetException]

COMPLETE = "complete"
READY = "ready"
INSTALLING = "installing"
PWR_ERROR = "pwr_error"
REMOVE = "remove"
INTERMEDIATE_INSTALL_STATES = [READY, INSTALLING]
FAILED_STATES = [PWR_ERROR, "error"]
