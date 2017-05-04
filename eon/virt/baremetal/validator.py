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

from eon.common import utils
from eon.virt import constants as virt_constant
from eon.openstack.common import log as logging
from eon.common import exception

LOG = logging.getLogger(__name__)


class BaremetalValidator(object):
    """ validate the resources data before adding/updating baremetal
    resource.
    """
    def __init__(self, data):
        self.data = data

    def validate_ilo_details(self):
        create_msg = "Verifying that ILO is reachable with provided details"
        error_msg = (_("Unable to communicate with the iLO"))
        log_error_msg = ("Unable to communicate with the iLO")
        corrective_msg = ("Verify that the ILO IP, Username and Password "
                          "given are correct and reachable")
        ilo_ip = self.data.get(virt_constant.EON_RESOURCE_ILO_IP)
        ilo_user = self.data.get(virt_constant.EON_RESOURCE_ILO_USER)
        ilo_pass = self.data.get(virt_constant.EON_RESOURCE_ILO_PASSWORD)
        if ilo_ip and ilo_pass and ilo_user:
            LOG.info(create_msg)
            try:
                # figure out a way to run ipmitool from mgmt node
                cmd = ("ipmitool -I lanplus -U %s -P %s -H %s power status" %
                       (ilo_user, ilo_pass, ilo_ip))
                cmd = cmd.split(" ")
                output = utils.run_command_get_output(cmd)
                if 'error' in output.lower():
                    raise
                return True
            except Exception:
                LOG.error(log_error_msg)
                LOG.warn(corrective_msg)
                raise exception.CreateException(error_msg)
