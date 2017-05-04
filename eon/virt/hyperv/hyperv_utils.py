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

import copy
import json
from eon import get_eon_loc
from eon.virt.hyperv import pywinrm
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.virt import constants as hyperv_const
from eon.openstack.common import log as logging
from eon.common import exception

LOG = logging.getLogger(__name__)

SCRIPT_DEST = 'activation.ps1'


SCRIPT_SRC = get_eon_loc() + "/virt/hyperv/scripts/activation.ps1"
PS_SCRIPT_TO_COPY_SCRIPT = '''$source = "%(script_src)s"
$destination = "%(script_dst)s"
Invoke-WebRequest $source -OutFile $destination
'''
PS_SCRIPT_TO_REMOVE_FILE = 'Remove-Item %(script_dst)s'


class HyperVUtils(object):

    def __init__(self, data):
        self.data = data
        self._script_path = ""
        self.session = pywinrm.get_pywinrm_session(
            data[hyperv_const.EON_RESOURCE_IP_ADDRESS],
            data[hyperv_const.EON_RESOURCE_PORT],
            data.get(hyperv_const.EON_RESOURCE_USERNAME),
            data.get(hyperv_const.EON_RESOURCE_PASSWORD),
        )

    def get_hostname(self):
        LOG.info("Getting HyperV host's hostname...")
        ps_script = hyperv_const.PS_SCRIPT_TO_GET_HOSTNAME
        resp = pywinrm.run_ps_script(
            self.session, ps_script)

        if resp.status_code != 0:
            raise exception.HyperVPSScriptError(
                err="%s" % resp.std_err)
        return resp.std_out.strip()

    def get_csv(self):
        LOG.info("Getting Cluster information...")
        ps_script = hyperv_const.PS_SCRIPT_TO_CHECK_CSV
        resp = pywinrm.run_ps_script(
            self.session, ps_script)
        if resp.status_code != 0:
            raise exception.HyperVPSScriptError(
                err="%s" % resp.std_err)
        return resp.std_out.strip()

    def _get_ps_script_for_validations(self):
        return '\n%s\n%s' % (
            hyperv_const.PS_SCRIPT_TO_CHK_OS,
            hyperv_const.PS_SCRIPT_TO_CHK_HYPERV_FEATURE)

    def _validate_pywinrm_response(self, resp):
        cmd_outs = resp.std_out.split()

        # Based on _get_pywinrm_ps_script, two std_out-s.
        if cmd_outs[0] != "True":
            raise exception.HyperVHostUnSupportedOSError()
        elif cmd_outs[1] != "True":
            raise exception.HyperVHostVirtualizationNotEnabledError()

    def _run_ps_script_through_pywinrm(self, ps_script):
        resp = pywinrm.run_ps_script(self.session, ps_script)

        if resp.status_code == 0:
            self._validate_pywinrm_response(resp)
        else:
            raise exception.HyperVPyWinRMExectionError()

    def _connectivity_check(self, update_data, cur_data):
        """Do a connection check only if connection related data
        is changed.
        """
        conn_keys = set((hyperv_const.EON_RESOURCE_IP_ADDRESS,
                         hyperv_const.EON_RESOURCE_PORT,
                         hyperv_const.EON_RESOURCE_USERNAME,
                         hyperv_const.EON_RESOURCE_PASSWORD))
        if set(update_data).isdisjoint(conn_keys):
            # Won't proceed if no value change for connection data.
            return

        new_data = copy.deepcopy(cur_data)
        new_data.update(update_data)

        # TODO: HTTPS for winrm connection using port 5986"
        session = pywinrm.get_pywinrm_session(
            new_data[hyperv_const.EON_RESOURCE_IP_ADDRESS],
            new_data[hyperv_const.EON_RESOURCE_PORT],
            new_data[hyperv_const.EON_RESOURCE_USERNAME],
            new_data[hyperv_const.EON_RESOURCE_PASSWORD])

        try:
            ps_script = hyperv_const.PS_SCRIPT_TO_GET_HOSTNAME
            resp = pywinrm.run_ps_script(
                session, ps_script)

            if resp.status_code != 0:
                raise exception.HyperVPSScriptError(
                    err="%s" % resp.std_err)

        except exception.PyWinRMAuthenticationError as exc:
            LOG.error("Pywinrm exception: %s while connecting to %s" % (exc,
                        new_data[hyperv_const.EON_RESOURCE_IP_ADDRESS]))
            raise exception.HyperVHostAuthenticationError()
        except exception.PyWinRMConnectivityError as exc:
            LOG.error("Pywinrm exception: %s while connecting to %s" % (exc,
                        new_data[hyperv_const.EON_RESOURCE_IP_ADDRESS]))
            raise exception.HyperVHostConnectivityError(err=exc.message)

    def _check_hyperv_host_using_pywinrm(self):
        """Validate if the HyperV host is supported with proper roles and
        basic services.

        :raises
            HyperVHostUnSupportedOSError,
            HyperVHostVirtualizationNotEnabledError,
            HyperVPyWinRMExectionError,
            HyperVHostAuthenticationError,
            HyperVHostConnectivityError
        """
        try:
            ps_script = self._get_ps_script_for_validations()
            self._run_ps_script_through_pywinrm(ps_script)
        except (exception.HyperVHostUnSupportedOSError,
                exception.HyperVHostVirtualizationNotEnabledError,
                exception.HyperVPyWinRMExectionError,
                ) as exc:
            raise exc
        except exception.PyWinRMAuthenticationError as exc:
            LOG.error("Pywinrm exception: %s while connecting to %s" % (exc,
                        self.data[hyperv_const.EON_RESOURCE_IP_ADDRESS]))
            raise exception.HyperVHostAuthenticationError()
        except exception.PyWinRMConnectivityError as exc:
            LOG.error("Pywinrm exception: %s while connecting to %s" % (exc,
                        self.data[hyperv_const.EON_RESOURCE_IP_ADDRESS]))
            raise exception.HyperVHostConnectivityError(err=exc.message)

    def _get_ps_script_to_copy_script(self):
        cmd = "%s" % (PS_SCRIPT_TO_COPY_SCRIPT)
        cmd = cmd % {"script_src": SCRIPT_SRC,
                     "script_dst": self.script_path}
        return cmd

    def _get_ps_script_to_remove_file(self):
        cmd = "%s" % (PS_SCRIPT_TO_REMOVE_FILE)
        cmd = cmd % {"script_dst": self.script_path}
        return cmd

    def _remove_activation_script(self):
        host_ip = self.data[hyperv_const.EON_RESOURCE_IP_ADDRESS]
        LOG.info("Removing the activation script from hyperv host %s",
                 host_ip)
        ps_script = self._get_ps_script_to_remove_file()

        resp = pywinrm.run_ps_script(self.session, ps_script)

        if resp.status_code != 0:
            LOG.warning("Deleting activation script from HyperV "
                        "host %s failed", host_ip)

    def _copy_ps_script(self):
        with open(SCRIPT_SRC, 'r') as fd:
            file_content = fd.read()
        final_script = hyperv_const.PS_SCRIPT_TO_STREAM_WRITE % {
            "file_name": self.script_path}\
                       + file_content +\
                       hyperv_const.PS_SCRIPT_TO_REPLACE_N
        resp = pywinrm.run_ps_script_copy_file(
            self.session,
            final_script)
        if resp.status_code == 0:
            LOG.info("File %(src)s successfully copied to %(dest)s" % {
                "src": SCRIPT_SRC, "dest": self.script_path})
        else:
            raise exception.HyperVPSScriptError(err="%s" % resp.std_err)

    def _execute_script(self):
        """
        :raises
            HyperVPSScriptError
        """
        try:
            resp_data = None
            ip = self.data[hyperv_const.EON_RESOURCE_IP_ADDRESS]
            self._copy_ps_script()
            resp = pywinrm.run_ps_script(
                self.session,
                self.script_path)
            if resp.status_code == 0:
                resp_data = json.loads(resp.std_out)
                LOG.info("Inventory data of hyperv host %(host)s : "
                         "%(inventory)s",
                         {"host": ip,
                          "inventory": resp_data})
                return resp_data
            else:
                raise exception.HyperVPSScriptError(err="%s" % resp.std_err)
        except exception as e:
            raise e
        finally:
            self._remove_activation_script()

    def get_host_validation_data(self, context):
        # execute the script and get all inventory data
        LOG.info("Getting the inventory data of hyperv host %s",
                 self.data[hyperv_const.EON_RESOURCE_IP_ADDRESS])
        collected_inventory = {}
        collected_inventory = self._execute_script()

        hux_obj = HLMFacadeWrapper(context)
        servers = hux_obj.get_server_by_role("MANAGEMENT-ROLE")
        hostname = hux_obj.model_generated_host_name(servers[0].get('id'))
        resp = pywinrm.run_ps_script(
            self.session,
            hyperv_const.PS_SCRIPT_TO_CHECK_TIME_SYNC %
            {"ntpserver_fqdn": hostname})
        if resp.status_code != 0:
            raise exception.HyperVPSScriptError(
                err="%s" % resp.std_err)
        collected_inventory['host_date_configured'] = resp.std_out.strip()
        return collected_inventory

    def get_temp_location(self):
        try:
            (std_out, std_err, status_code) = pywinrm.run_cmd_low_level(
                self.session, hyperv_const.CMD_SCRIPT_TO_GET_TEMP_LOC)

            if status_code != 0:
                raise exception.HyperVPSScriptError(
                    err="%s" % std_err)
            return std_out.strip()

        except exception.PyWinRMAuthenticationError as exc:
            LOG.error("Pywinrm exception: %s while connecting to %s" % (exc,
                        self.data[hyperv_const.EON_RESOURCE_IP_ADDRESS]))
            raise exception.HyperVHostAuthenticationError()
        except exception.PyWinRMConnectivityError as exc:
            LOG.error("Pywinrm exception: %s while connecting to %s" % (exc,
                        self.data[hyperv_const.EON_RESOURCE_IP_ADDRESS]))
            raise exception.HyperVHostConnectivityError(err=exc.message)

    @property
    def script_path(self):
        if not self._script_path:
            self._script_path = self.get_temp_location() + "\\" + SCRIPT_DEST
        return self._script_path
