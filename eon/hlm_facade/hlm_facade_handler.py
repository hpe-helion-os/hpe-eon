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

import time
import itertools
from functools import partial
from functools import wraps
import constants as facade_constants
from eon.hlm_facade import http_requests
from eon.hlm_facade import exception as facade_exceptions
from eon.openstack.common import log as logging
from oslo_config import cfg

HLM_UX_SERVICES = [cfg.StrOpt('hux_services_url',
                              default="http://localhost:9085",
                              help='Endpoint of node running hlm ux services')
                   ]

CONF = cfg.CONF
hlm_ux_services_group = cfg.OptGroup(name='hlm_ux_service',
                                     title='Options for the hlm ux services')
CONF.register_group(hlm_ux_services_group)
CONF.register_opts(HLM_UX_SERVICES, hlm_ux_services_group)

LOG = logging.getLogger(__name__)


def retry(func):
    @wraps(func)
    def originalDeco(*args, **kwargs):
        # initial count: 5; increment with: 7
        retries = kwargs.get('retries', facade_constants.RETRY_COUNT)
        max_delay = kwargs.get('max_delay', facade_constants.MAX_INTERVAL)
        sleep_count = itertools.count(5, 7)
        for i in xrange(0, retries):
            try:
                return func(*args, **kwargs)
            except facade_exceptions.RetryException as re:
                if i < retries - 1:
                    LOG.info("Waiting for the playbook run to complete. "
                             "Retry count: %s" % i)
                    time.sleep(min(sleep_count.next(), max_delay))
                    continue
                if re.cleanup:
                    re.cleanup()
                raise facade_exceptions.TimeoutError(_("Timed out running "
                                                     "playbook"))
    return originalDeco


class HLMFacadeWrapper(object):
    """
    Wrapper around hlm-ux-services.
    Provide methods to invoke rest calls which retrieves/updates
    HLM input model.
    """
    def __init__(self, context):
        self.context = context
        self.endpoint_url = CONF.hlm_ux_service.hux_services_url

    def _ks_auth_header(self):
        """ Get the auth token from context
        """
        return {'X-Auth-Token': self.context.auth_token}

    @retry
    def _get_status(self, pRef, **kwargs):
        url = ("%s%s/%s" % (self.endpoint_url, facade_constants.PLAYS,
                            pRef))
        resp = http_requests.get(url, headers=self._ks_auth_header())
        resp_code = resp.get('code')
        if resp_code == 0:
            return resp
        elif resp_code and resp_code != 0:
            CommandString = resp.get('commandString')
            message = (_("Playbook: '%s' run failed. Check ansible logs "
                       "[%s, %s] on deployer for more details for "
                       "process[%s].")
                       % (logging.mask_password(CommandString),
                          '~/.ansible/ansible.log',
                          '/var/log/configuration_processor/errors.log',
                          pRef))
            LOG.error("%s" % message)
            raise facade_exceptions.GetException("%s. Status Code: %s"
                                                 % (message, resp_code))
        else:
            kill_process = partial(self._kill_play, pRef)
            raise facade_exceptions.RetryException(cleanup=kill_process)

    def commit_changes(self, id_, task):
        """ Commit input model changes
        """
        url = ("%s%s" % (self.endpoint_url, facade_constants.COMMIT_URL))
        LOG.info("[%s] Committing changes to input model for %s task" %
                 (id_, task))
        body = {'message': facade_constants.COMMIT_MESSAGE % (id_, task)}
        return http_requests.post(url, body, headers=self._ks_auth_header())

    def revert_changes(self):
        """ Revert input model changes.
        """
        url = ("%s%s" % (self.endpoint_url, facade_constants.REVERT_URL))
        LOG.info("Reverting input model changes")
        return http_requests.delete(url, headers=self._ks_auth_header())

    def get_model(self):
        """ Get complete input model.
        """
        url = ("%s%s" % (self.endpoint_url, facade_constants.INPUT_MODEL_URL))
        LOG.info("Retrieving complete input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def update_model(self, model):
        """ Update complete input model.
        """
        url = ("%s%s" % (self.endpoint_url, facade_constants.INPUT_MODEL_URL))
        LOG.info("Updating complete input model")
        http_requests.post(url, body=model, headers=self._ks_auth_header())

    def get_hostnames(self):
        """ Get all the cp generated hostname for all servers
            return {'server-id1': cp-generated-hostname1,
                     'server-id2': cp-generated-hostname2, .... }
        """
        url = ("%s%s" % (self.endpoint_url,
                         facade_constants.CP_OUTPUT_SERVER_INFO))
        LOG.info("Retrieving CP output for servers_info_yml")
        servers = http_requests.get(url, headers=self._ks_auth_header())
        hostnames = dict()
        for key in servers:
            hostnames[key] = servers[key]['hostname']
        return hostnames

    def get_model_expanded(self, id_=None):
        """ Get detailed input model
        """
        if not id_:
            url = ("%s%s" % (self.endpoint_url,
                             facade_constants.EXPANDED_INPUT_MODEL_URL))
        else:
            url = ("%s%s/%s" % (self.endpoint_url,
                                facade_constants.EXPANDED_INPUT_MODEL_SERVERS,
                                id_))
        LOG.info("Retrieving expanded input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_controlplanes(self):
        """ Get servers data from input model
        """
        url = ("%s%s" % (self.endpoint_url,
                         facade_constants.CONTROLPLANES_URL))
        LOG.info("Retrieving servers.yml from input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_servers(self):
        """ Get servers data from input model
        """
        url = ("%s%s" % (self.endpoint_url, facade_constants.SERVERS_URL))
        LOG.info("Retrieving servers.yml from input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_server_by_id(self, id_):
        url = ("%s%s/%s" % (self.endpoint_url, facade_constants.SERVERS_URL,
                            id_))
        LOG.info("[%s] Retrieving servers.yml from input model" % id_)
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_interfaces_by_id(self, id_):
        url = ("%s%s/%s" % (self.endpoint_url, facade_constants.INTERFACES_URL,
                            id_))
        LOG.info("[%s] Retrieving interfaces from input model" % id_)
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_networks(self):
        """ Get servers data from input model
        """
        url = ("%s%s" % (self.endpoint_url, facade_constants.NETWORKS_URL))
        LOG.info("Retrieving networks from input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_network_groups(self):
        """ Get servers data from input model
        """
        url = ("%s%s" % (self.endpoint_url,
                         facade_constants.NETWORKS_GROUPS_URL))
        LOG.info("Retrieving network groups from input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_server_groups(self):
        """ Get servers data from input model
        """
        url = ("%s%s" % (self.endpoint_url,
                         facade_constants.SERVER_GROUPS_URL))
        LOG.info("Retrieving server groups from input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def get_interfaces_by_name(self, name):
        """ Get servers data from input model
        """
        url = ("%s%s/%s" % (self.endpoint_url, facade_constants.INTERFACES_URL,
                            name))
        LOG.info("Retrieving interfaces from input model")
        return http_requests.get(url, headers=self._ks_auth_header())

    def create_server(self, model):
        """ Update servers data in input model
        """
        url = ("%s%s" % (self.endpoint_url, facade_constants.SERVERS_URL))
        LOG.info("Updating input model with data: %s"
                 % logging.mask_password(model))
        http_requests.post(url, body=model, headers=self._ks_auth_header())
        LOG.info("Updated input model successfully")

    def update_server_by_id(self, model, id_):
        data = self.get_server_by_id(id_)
        url = ("%s%s/%s" % (self.endpoint_url, facade_constants.SERVERS_URL,
                            id_))
        data.update(model)
        http_requests.put(url, body=data, headers=self._ks_auth_header())
        LOG.info("[%s] Updated input model successfully" % id_)

    def delete_server(self, id_):
        url = ("%s%s/%s" % (self.endpoint_url, facade_constants.SERVERS_URL,
                            id_))
        http_requests.delete(url, headers=self._ks_auth_header())
        LOG.info("Deleted %s from hlm input model" % id_)

    def _run(self, url, body=None):
        """ Execute a play and get corresponding process reference to
        track the play.
        """
        resp = http_requests.post(url, body, headers=self._ks_auth_header())
        return resp.get('pRef')

    def _kill_play(self, process_ref):
        """ Interrupt a play by killing (SIGINT) the process.
        """
        url = ("%s%s/%s" % (self.endpoint_url, facade_constants.PLAYS,
                            process_ref))
        LOG.info("Force killing the play with process "
                 "ref %s" % str(process_ref))
        try:
            http_requests.delete(url, headers=self._ks_auth_header())
        except facade_exceptions.NotFound:
            LOG.warning("The play with process ref"
                        " %s was not found. Ignoring.." % str(process_ref))

    def config_processor_run(self, body=None):
        """ Run config processor and return status of the job
        """
        url = ("%s%s" % (self.endpoint_url,
                         facade_constants.CONFIG_PROCESSOR_RUN))
        LOG.info("Executing config processor run")
        process_ref = self._run(url, body)
        return self._get_status(process_ref)

    def ready_deployment(self):
        """ Run ready deployment
        """
        url = ("%s%s" % (self.endpoint_url,
                         facade_constants.READY_DEPLOYMENT))
        LOG.info("Executing ready deployment")
        process_ref = self._run(url)
        return self._get_status(process_ref)

    def cobbler_deploy(self, id_, password):
        """ API call to re-image baremetal server and install OS.
        """
        server_model = self.get_server_by_id(id_)
        # Create payload for cobbler deploy
        body = {"servers": [server_model],
                "baremetal": {"hlmuser_password": password,
                              "disable_pwd_auth": "false"}}
        url = self.endpoint_url + facade_constants.OSINSTALL
        LOG.info("Os Install begins on %s" % id_)
        http_requests.post(url, body=body, headers=self._ks_auth_header())

    @retry
    def cobbler_deploy_status(self, id_, **kwargs):
        """ Get the status of os install
        """
        url = self.endpoint_url + facade_constants.OSINSTALL
        resp = http_requests.get(url, headers=self._ks_auth_header())
        res_deployment_status = resp.get('servers').get(id_)
        if res_deployment_status in facade_constants.FAILED_STATES:
            raise facade_exceptions.CobblerException(
                _("[%s]: Failed to install operating system") % id_)
        elif res_deployment_status == facade_constants.COMPLETE:
            LOG.info("[%s]: OS installed successfully" % id_)
            return res_deployment_status
        else:
            raise facade_exceptions.RetryException()

    def model_generated_host_name(self, ids):
        """ Get input model generated hostnames
        :param ids can be a string or a list
        :return  hostnames of type 'str'
        """
        resp = self.get_hostnames()
        if isinstance(ids, list):
            verb_hosts = []
            for id_ in ids:
                name = resp.get(id_)
                verb_hosts.append(name)
            verb_hosts = ",".join(verb_hosts)
        else:
            verb_hosts = resp.get(ids)
        return verb_hosts

    def get_server_by_role(self, role_name):
        servers = self.get_servers()
        server_with_same_role = []
        for server in servers:
            if server.get('role') == role_name:
                server_with_same_role.append(server)
        return server_with_same_role

    def run_playbook_by_ids(self, play, ids, tags=None,
                            extra_args=None, **kwargs):
        limit = self.model_generated_host_name(ids)
        return self.run_playbook(play, limit=limit, tags=tags,
                                 extra_args=extra_args,
                                 **kwargs)

    def run_playbook(self, play, limit='localhost', tags=None,
                     extra_args=None, **kwargs):
        body = {}
        if limit:
            body.update({"limit": limit})
        if tags:
            body.update({"tags": tags})
        if extra_args and isinstance(extra_args, dict):
            body.update(extra_args)
        LOG.info("Running playbook %s for [%s] with tags [%s]"
                 % (facade_constants.PLAYBOOK_MAP[play], limit, tags))
        url = self.endpoint_url + facade_constants.PLAYBOOK_MAP[play]
        process_ref = self._run(url, body=body)
        return self._get_status(process_ref, **kwargs)

    def run_monitoring_playbooks(self):
        """Method to run hlm monitoring playbooks
        1. First will configure host_alive plugin on all monitoring appliances
        2. Second will update the etc/hosts file on MON appliances
        """
        self.run_playbook('monasca-deploy',
                          limit=None,
                          tags="active_ping_checks")
        self.run_playbook('site', limit='MON-API', tags='generate_hosts_file')

    def add_empty_pass_through(self):
        """Add pass_through.yml if not present in the input model"""
        # Get the full model
        # Insert the pass_through stuff
        # Update the input model

        filename = 'data/pass_through.yml'
        key = 'pass-through'
        sections_dict = {key: [filename]}
        filesectionmap_dict = {filename: ['product', key]}
        inputmodel_dict = {key: {'servers': [], 'global': {}}}

        model = self.get_model()
        fileInfo = model.get("fileInfo")
        files = fileInfo.get("files")
        sections = fileInfo.get("sections")
        filesectionmap = fileInfo.get("fileSectionMap")
        product = sections.get('product')

        files.append(filename)
        product.append(filename)

        sections.update(sections_dict)
        filesectionmap.update(filesectionmap_dict)
        model.get("inputModel").update(inputmodel_dict)

        self.update_model(model)

    def get_pass_through(self):
        """ Get pass through yml contents """
        LOG.info("Retrieving pass through yml from input model")
        url = ("%s%s" % (self.endpoint_url, facade_constants.PASS_THROUGH_URL))
        try:
            resp = http_requests.get(url, headers=self._ks_auth_header())
            LOG.debug("Pass through contents: %s" % resp)
            return resp
        except facade_exceptions.NotFound:
            raise facade_exceptions.NotFound(
                'Could not find pass_through.yml in the input model, '
                'please create one or get a copy from the example input '
                'models')
            # We may want to put this back in someday if we make hlm-ux-service
            # do a better job deep-comparing objects:
            # self.add_empty_pass_through()
            # resp = http_requests.get(url, headers=self._ks_auth_header())
            # LOG.debug("Pass through contents: %s" % resp)
            # return resp

    def update_pass_through(self, body):
        url = ("%s%s" % (self.endpoint_url,
                         facade_constants.PASS_THROUGH_URL))
        return http_requests.put(url, body, headers=self._ks_auth_header())
