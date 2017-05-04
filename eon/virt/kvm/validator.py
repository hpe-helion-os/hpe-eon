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

from eon.common.ssh_utilities import RemoteConnection
from eon.virt import constants as virt_constant
from eon.openstack.common import log as logging
from eon.common import exception

LOG = logging.getLogger(__name__)


class KVMValidator(object):
    """ Validates the parameter provided while performing CRUD operations
    on hlinux and rhel resources
    """
    def __init__(self, data):
        self.data = data
        self.remote_connection = RemoteConnection(self.data.get("ip_address"),
                                                  self.data.get("username"),
                                                  self.data.get("password"))

    def validate_ssh_connection(self):
        create_msg = "Verifying that ssh is enabled with provided details"
        error_msg = _("Unable to ssh into the machine")
        corrective_msg = ("Verify that the IP, Username and Password "
                          "given are correct and reachable")
        ip = self.data.get(virt_constant.EON_RESOURCE_IP_ADDRESS)
        user = self.data.get(virt_constant.EON_RESOURCE_USERNAME)
        passwd = self.data.get(virt_constant.EON_RESOURCE_PASSWORD)
        if ip and passwd and user:
            LOG.info(create_msg)
            try:
                rem_connect = RemoteConnection(ip, user, passwd)
                rem_connect.open_connection()
                return rem_connect.is_connected()
            except Exception:
                LOG.warn(corrective_msg)
                LOG.error(error_msg)
                raise exception.CreateException(error_msg)
            finally:
                rem_connect.close_connection()

    def check_instances(self):
        activation_msg = ('Verifying that no instances are defined on '
                            'remote host')
        LOG.info(activation_msg)
        try:
            exit_code, std_out = self._run_virsh_list()
            self._check_for_instances(exit_code, std_out)
        except Exception as exc:
            LOG.exception(exc)
            LOG.warn("Ignoring error - %s" % str(exc))

    def _run_virsh_list(self):
        (exit_code, std_out, _std_err) = (
            self.remote_connection.exec_command_and_wait(
                "virsh list --all"))
        return exit_code, std_out

    def _check_for_instances(self, exit_code, std_out):
        if (exit_code == 0 and std_out):
            lines = std_out.split('\n')
            words = [line.split() for line in lines if len(line.strip()) > 0]
            if len(words) > 2 and len(words[2]) > 2:
                # The first line is the title line, the second line is the
                # separator.
                error_msg = ("Virtual machines are already running "
                             "on the kvm host")
                corrective_action = ("Manually remove these instances "
                                     "using the same tools that you "
                                     "used to manage the instances. "
                                     "Instances consume resources and "
                                     "may cause oversubscription when "
                                     "not managed by HPE Helion CloudSystem")
                LOG.warn(error_msg)
                LOG.warn(corrective_action)
        else:
            LOG.warn("Could not check for running instances "
                       "on the kvm host.")

    def preactivation_check(self):
        self.check_instances()
