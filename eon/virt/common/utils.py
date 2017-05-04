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

import eon.db
from eon.common import exception
from eon.virt import constants as eon_const
from eon.openstack.common import log as logging
from eon.openstack.common import context as context_
from oslo_config import cfg
import requests
import subprocess
import time
from eon.virt import constants
from eon.hlm_facade import hlm_facade_handler
from webob import exc as web_exc

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

# In secs.
NOVA_API_RETRY_INTERVAL = 10
NEUTRON_API_RETRY_INTERVAL = 10
NEUTRON_MAX_TIMEOUT = 180

opt = [
     cfg.StrOpt('eon_rsa_pem_file',
               default='',
               help='path of the pem file with encryption key for eon-encrypt')
      ]
CONF.register_opts(opt)


class VirtCommonUtils(object):
    def __init__(self):
        self.db_api = eon.db.get_api()
        self.db_api.setup_db_env()

    def update_prop(self, context, rsrc_id, prop, prop_value):
        db_session_event = ('update-%s' % prop)
        try:
            LOG.debug("Updating resource: %s's %s to %s" % (
                                                    rsrc_id, prop, prop_value))
            db_session = self.db_api.get_transactional_session(
                db_session_event)
            values = {prop: prop_value}
            self.db_api.update_resource(context,
                                        rsrc_id,
                                        values,
                                        session=db_session)

            self.db_api.commit_session(db_session_event, db_session)
            LOG.info("Updated the resource [%s] %s to: %s" %
                     (rsrc_id, prop, prop_value))
        except Exception as e:
            msg = (_("Updating 'eon resource %s' failed. Error: "
                     "'%s'") % (prop, e.message))
            log_msg = (("Updating 'eon resource %s' failed. Error: "
                     "'%s'") % (prop, e.message))
            LOG.error(log_msg)
            raise exception.UpdateException(msg=msg)

    def create_servers_payload(self, body, db_data):
        hlm_payload = {}
        # base payload for provision and activate
        for key in eon_const.PROVISION_PAYLOAD + eon_const.ACTIVATE_PAYLOAD:
            value = db_data.get(key)
            if value:
                hlm_payload[eon_const.HLM_PAYLOAD_MAP[key]] = value
        # process resource properties for provision
        props = db_data.get(eon_const.EON_RESOURCE_META_KEY)
        if props:
            for item in props:
                key = item.get('name')
                value = item.get('value')
                if key in eon_const.PROVISION_PAYLOAD_METADATA:
                    hlm_payload[eon_const.HLM_PAYLOAD_MAP[key]] = value
        # final processing for rhel os version
        osv = body.get(eon_const.VERSION)
        if osv:
            hlm_payload[eon_const.COBBLER_PROFILE] = (
                eon_const.COBBLER_PROFILE_MAP[osv])
        # for san booted device this param is required in servers.yml
        boot_from_san = body.get(eon_const.BOOT_FROM_SAN)
        if boot_from_san:
            hlm_payload[eon_const.HLM_PAYLOAD_MAP[
                eon_const.BOOT_FROM_SAN]] = boot_from_san
            # An extra - "multipath" attribute has to be attached to the
            # cobbler profile. This is explicitly for rhel today.
            if osv:
                distro_id = eon_const.COBBLER_PROFILE_MAP[osv] + "-multipath"
                hlm_payload[eon_const.COBBLER_PROFILE] = distro_id

        raw_properties = body.get('property')
        if raw_properties:
            for datum in raw_properties:
                key, value = datum.split('=', 1)
                hlm_payload[key] = value
        return hlm_payload

    def modify_servers_payload(self, input_model_data, db_data, resource_type):
        if resource_type == eon_const.EON_RESOURCE_TYPE_HYPERV:
            username = db_data.get(eon_const.EON_RESOURCE_USERNAME)
            password = db_data.get(eon_const.EON_RESOURCE_PASSWORD)
            encrypted_password = get_encrypted_password(password)
            payload_key = eon_const.HLM_PAYLOAD_MAP[
                eon_const.EON_RESOURCE_ANSIBLE_OPTIONS]
            port = str(db_data.get(eon_const.EON_RESOURCE_PORT,
                                   eon_const.HYPERV_DEFAULT_PORT))
            payload_val = eon_const.HYPERV_ANSIBLE_OPTIONS % (username,
                                                            encrypted_password,
                                                             port)
            input_model_data[payload_key] = payload_val
            input_model_data.pop(
                eon_const.HLM_PAYLOAD_MAP[eon_const.NIC_MAPPINGS], None)
        return input_model_data


def get_nova_hypervisor_info(url, headers, resource_name, action=None):
    """
    :param resource_name : host name or clustername(cluster-moid)
    :param url : nova api url
    :param headers : API header
    periodically makes the api call.(nova hypervisor-list)
    interval_sec: At what interval api class to be made.get
    max_timeout_sec: Max timeout to wait for.
    """
    interval_sec = NOVA_API_RETRY_INTERVAL
    max_timeout_sec = constants.NOVA_HYPERVISOR_LIST_TIMEOUT
    total_function_calls = max_timeout_sec / interval_sec
    for _ in xrange(total_function_calls):
        # Returns the dict, which contains the list of hypervisors.
        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.ConnectionError as e:
            LOG.error(e)
            LOG.info("Trying to reconnect ...")
            time.sleep(interval_sec)
            continue

        hypervisors = response.json()['hypervisors']
        LOG.info(" The list of hypervisors : %s " % hypervisors)
        # Checks whether the record is successfully updated.
        if action == constants.ACTIVATION:
            id_ = -1
            for hyp in hypervisors:
                if resource_name.lower() == hyp["hypervisor_hostname"].lower():
                    # TODO: ensure for hyper-V post-activation
                    # To solve the issue where hypervisor is not removed from
                    # the hypervisor
                    id_ = hyp["id"] if id_ < hyp["id"] else id_
                    return id_

        elif action == constants.DEACTIVATION:
            hypervisors_list = [hyp.values()[1] for hyp in hypervisors]
            if resource_name not in hypervisors_list:
                return True

        LOG.info("Waiting for node:  %s to be updated..." % resource_name)
        time.sleep(interval_sec)
    return None


def check_neutron_agent_list(
        url, headers, host_name, agent_type, action=constants.ACTIVATION):
    """ """
    interval_sec = NEUTRON_API_RETRY_INTERVAL
    max_timeout_sec = NEUTRON_MAX_TIMEOUT
    total_function_calls = max_timeout_sec / interval_sec
    for i in xrange(total_function_calls):
        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.ConnectionError as e:
            LOG.error(e)
            LOG.info("Trying to reconnect ...")
            time.sleep(interval_sec)
            continue

        agents = response.json().get('agents')
        if agents:
            neutron_agent_status = _check_neutron_agent_status(
                agents, host_name, agent_type)
            if action == constants.ACTIVATION:
                if neutron_agent_status:
                    return True
                LOG.info("Neutron agent is not up and running, Retrying...")
            elif action == constants.DEACTIVATION:
                if not neutron_agent_status:
                    return True
                LOG.info("Neutron agent is still up and running, "
                           "Retrying...")

        time.sleep(interval_sec)

    return False


def _check_neutron_agent_status(agents, host_name, agent_type):
    for agent in agents:
        if (agent["host"].lower() == host_name.lower() and
                agent['agent_type'] == agent_type):
                    return agent["alive"]

    return False


def get_global_pass_thru_data(context, key):
    hlmfacwrap = hlm_facade_handler.HLMFacadeWrapper(context)
    pass_thru_data = hlmfacwrap.get_pass_through()
    return pass_thru_data.get("global").get(key)


def validate_nova_neutron_list(context, id_, db_api,
                               hypervisor_hostname,
                               neutron_agent_type,
                               action,
                               validate_neutron=True):
    nova_url, headers = get_nova_hypervisor_rest_api(context, CONF.nova.url)
    nova_hyper_id = get_nova_hypervisor_info(
               nova_url, headers, hypervisor_hostname, action)
    if not nova_hyper_id:
        msg = _("Nova Hypervisor '%s' not found" % hypervisor_hostname)
        raise exception.NovaHypervisorNotFoundException(
            resource_name=hypervisor_hostname, err=msg)
    db_api.create_property(context,
                           id_,
                           "hypervisor_id",
                           nova_hyper_id)
    if validate_neutron:
        (neutron_url, headers) = get_neutron_agent_rest_api(context,
                                                            CONF.neutron.url)
        if not check_neutron_agent_list(
                neutron_url, headers, hypervisor_hostname, neutron_agent_type):
            msg = _("Neutron agent for '%s' not found" % hypervisor_hostname)
            raise exception.NeutronAgentNotFoundException(
                resource_name=hypervisor_hostname, err=msg)


def get_headers(context):
    headers = None
    if context.auth_token:
        headers = {'X-Auth-Token': context.auth_token,
                   'Content-Type': 'application/json',
                   }
    else:
        LOG.error("Auth Token not available in context."
                  "This is required to make PAVMMS call")
        # Need to raise exception here.
    return headers


def get_nova_hypervisor_rest_api(context, url):
    auth_dict = context_.get_service_auth_info(CONF.nova)
    url = url + '/v2.1/' + auth_dict['tenant_id'] + '/os-hypervisors'
    LOG.info("Successfully got the foundation keystone data")
    headers = {'User-Agent': 'eon-conductor',
               'X-Auth-Token': auth_dict['auth_token'],
               'accept': 'application/json',
               }
    return url, headers


def get_nova_hypervisor_show_api(context, url):
    auth_dict = context_.get_service_auth_info(CONF.nova)
    url = url + '/v2.1/' + auth_dict['tenant_id'] + '/os-hypervisors/detail'
    LOG.info("Successfully got the foundation keystone data")
    headers = {'User-Agent': 'eon-conductor',
               'X-Auth-Token': auth_dict['auth_token'],
               'accept': 'application/json',
               }
    return url, headers


def get_neutron_agent_rest_api(context, url, id_=None):
    auth_dict = context_.get_service_auth_info(CONF.neutron)
    if id_:
        url = url + '/v2.0/agents/' + id_ + '.json'
    else:
        url = url + "/v2.0/agents.json"
    headers = {'User-Agent': "eon-conductor",
               'X-Auth-Token': auth_dict['auth_token'],
               'accept': 'application/json',
               }
    return url, headers


def check_for_running_vms(self, context, hypervisor_hostname,
                          resource_inventory):
    try:
        nova_url, headers = get_nova_hypervisor_show_api(
                                        context, CONF.nova.url)
        response = requests.get(nova_url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        LOG.error(e)
        LOG.info("Trying to reconnect ...")
        (nova_url, headers) = get_nova_hypervisor_show_api(context,
                                                           CONF.nova.url)
        response = requests.get(nova_url, headers=headers)
    hypervisors = response.json()['hypervisors']
    LOG.info(" The list of hypervisors : %s " % hypervisors)
    for hyp in hypervisors:
        if hypervisor_hostname.lower() == hyp["hypervisor_hostname"].lower():
            if hyp["running_vms"]:
                resource_name = resource_inventory['id']
                msg = _("VMs already running in the compute")
                raise exception.DeactivationFailure(
                            resource_name=resource_name, err=msg)


def check_ovsvapp_agent_status(agents, ovsvapp_names):
    """
    Returns the status of the ovsvapp agents, which includes
    error'd and successful ovsvapp deployments.
    """
    LOG.debug("Neutron agent status %s" % agents)
    agents_status = [{ovsvapp_name:
            {"errors":
                _("%s on the host %s is not up" % (ovsvapp_name,
                    agent['configurations']['esx_host_name']))
                        if agent['alive'] is False else None,
            "success":
                _(" %s on the host %s is up and running " % (ovsvapp_name,
                    agent['configurations']['esx_host_name']))
                        if agent['alive'] is True else None
            }
        }
        for agent in agents for ovsvapp_name in ovsvapp_names
            if (agent.get("configurations").
                get("esx_host_name") == ovsvapp_name and
                agent['agent_type'] == "OVSvApp Agent")]

    errors = []
    success = []

    for agent in agents_status:
        for ovs in ovsvapp_names:
            if agent.get(ovs):
                errors.append(agent[ovs]["errors"]) \
                    if agent[ovs]["errors"] else \
                        success.append(agent[ovs]["success"])
    if not errors:
        return success

    LOG.warn("Errors observed in the OVSvAPP agent: %s" % errors)


def check_ovsvapp_agent_list(context, hypervisor_hostname,
                             resource_inventory, timeout_sec=None):
    """
    Checks the OVSvAPP agent status
    """
    interval_sec = NEUTRON_API_RETRY_INTERVAL
    (neutron_url, headers) = get_neutron_agent_rest_api(context,
                                                        CONF.neutron.url)
    hosts = resource_inventory.get('inventory').get('hosts')
    if timeout_sec:
        max_timeout_sec = timeout_sec
    else:
        max_timeout_sec = (len(hosts) *
                           eon_const.CHECK_L2AGENT_TIMEOUT_PER_HOST)

    total_function_calls = max_timeout_sec / interval_sec
    ip_list = []
    for ip in hosts:
        ip['name'] = unicode(ip['name'])
        ip_list.append(ip["name"])
    for _ in xrange(total_function_calls):
        try:
            response = requests.get(neutron_url, headers=headers, verify=False)
        except requests.exceptions.ConnectionError as e:
            LOG.error(e)
            LOG.info("Trying to reconnect ...")
            time.sleep(interval_sec)
            continue

        agents = response.json().get('agents')
        if agents:
            ovsvapp_names = ip_list
            status = check_ovsvapp_agent_status(agents, ovsvapp_names)
            if status:
                LOG.info("OVSvAPP agents are up and running for"
                         "all hosts in the esx cluster.")
                return status

        LOG.info("OVSvAPP agents are not up Trying again...")
        time.sleep(interval_sec)
    raise exception.OVSvAPPNotUpException(
            resource_name=hypervisor_hostname)


def get_hypervisor_roles(hux_obj, hypervisor_type):
    control_planes = hux_obj.get_controlplanes()
    control_plane_hypervisor = []
    server_roles_filters = []
    if hypervisor_type in [eon_const.EON_RESOURCE_TYPE_HLINUX,
                           eon_const.EON_RESOURCE_TYPE_RHEL]:
        server_roles_filters.append('nova-compute-kvm')
    elif hypervisor_type == eon_const.EON_RESOURCE_TYPE_HYPERV:
        server_roles_filters.append('nova-compute-hyperv')
    for plane in control_planes:
        for resource in plane.get('resources'):
            for component in resource.get('service-components'):
                if component in server_roles_filters:
                    control_plane_hypervisor.append(resource)
    role_names = []
    for plane_hypervisor in control_plane_hypervisor:
        role_names.append(plane_hypervisor.get("server-role"))
    return role_names


def get_server_groups_with_no_child(hux_obj):
    all_server_groups = hux_obj.get_server_groups()
    server_groups = []
    for server_group in all_server_groups:
        has_srv_grp = server_group.get("server-groups", None)
        if not has_srv_grp:
            server_groups.append(server_group)
    return server_groups


def get_nova_hypervisor_service_api(context, url, id_):
    auth_dict = context_.get_service_auth_info(CONF.nova)
    url = url + '/v2.1/' + auth_dict['tenant_id'] + '/os-services/' + id_
    return url


def get_nova_url(context):
    return CONF.nova.url


def get_nova_hypervisor_list(nova_url, headers):
    try:
        response = requests.get(nova_url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        LOG.error(e)
        LOG.info("Trying to reconnect ...")
        response = requests.get(nova_url, headers=headers)
    hypervisors = response.json()['hypervisors']
    return hypervisors


def get_neutron_url(context):
    return CONF.neutron.url


def get_neutron_agent_list(self, context, neutron_url=None):
    if neutron_url is None:
        neutron_url = get_neutron_url(context)
    try:
        neutron_rest_url, headers = get_neutron_agent_rest_api(
                                    context, neutron_url)
        response = requests.get(neutron_rest_url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        LOG.error(e)
        LOG.info("Trying to reconnect ...")
        (neutron_rest_url, headers) = self.get_neutron_agent_rest_api(
                                      context, neutron_url)
        response = requests.get(neutron_rest_url, headers=headers)
    neutron_agents = response.json()['agents']
    return neutron_agents


def delete_nova_service(context, host_name):
    """Delete nova-service from the controller.
    :param host_name: hostname of the controller from where we are removing
    the entry of nova
    """
    nova_rest_url, headers = get_nova_hypervisor_show_api(context,
                                                          CONF.nova.url)
    hypervisors = get_nova_hypervisor_list(nova_rest_url, headers)
    if not hypervisors:
        log_msg = "Deleting service: nova failed.No nova hypervisors found"
        LOG.warn(log_msg)
        return False
    for hypervisor in hypervisors:
        if hypervisor.get('hypervisor_hostname').lower() == host_name.lower():
            id = str(hypervisor.get('service').get('id'))
            nova_service_url = get_nova_hypervisor_service_api(
                context, CONF.nova.url, id)
            LOG.info(nova_service_url)
            break
    else:
        log_msg = ("Deleting nova service with id %s failed." %
                   hypervisor.get('service').get('id'))
        LOG.warn(log_msg)
        return False

    response = requests.delete(nova_service_url, headers=headers, verify=False)
    LOG.info(response.status_code)
    if response.status_code == web_exc.HTTPNoContent.code:
        msg = "Deleting nova service with id %s succeeded"
        msg = msg % (hypervisor.get('service').get('id'))
        LOG.info(msg)
        return True

    log_msg = ("Deleting nova service with id %s failed "
               "with status code: %d")
    log_msg = log_msg % (hypervisor.get('service').get('id'),
                         response.status_code)
    LOG.warn(log_msg)
    return False


def delete_neutron_service(self, context, hypervisor_hostname):
    """Delete neutron-service from the controller.
    """
    neutron_url = get_neutron_url(context)
    neutron_agents = get_neutron_agent_list(self, context, neutron_url)
    if not neutron_agents:
        log_msg = ("Deleting service: neutron failed.No neutron agents found")
        LOG.warn(log_msg)
        return False
    for agent in neutron_agents:
        if agent.get('host').lower() == hypervisor_hostname.lower():
            resp_id = agent.get("id")
            neutron_serv_url, headers = get_neutron_agent_rest_api(
                              context, neutron_url, resp_id)
            LOG.info("Deleting neutron agent with id %s "
                      % (resp_id))
            response = requests.delete(neutron_serv_url, headers=headers,
                                        verify=False)
            LOG.info(response.status_code)
            if(response.status_code == web_exc.HTTPNoContent.code):
                msg = "Deleting neutron agent with id %s succeeded"
                msg = msg % (resp_id)
                LOG.info(msg)
            else:
                log_msg = ("Deleting neutron agent with id %s failed "
                           "with status code: %d")
                log_msg = log_msg % (resp_id, response.status_code)
                LOG.warn(log_msg)
                return False


def check_if_os_config_ran(remote_connection):
    return remote_connection.does_file_exist(constants.OSCONFIG_RAN_MARKER)


def get_encrypted_password(password):
    rsa_pem_file = CONF.eon_rsa_pem_file
    proc = subprocess.Popen(['/usr/bin/eon-encrypt', password,
                                     '-k', rsa_pem_file],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
    for line in proc.stdout:
        encrypted_password = line.strip()
    return encrypted_password
