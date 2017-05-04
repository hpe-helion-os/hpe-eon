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

from eon.openstack.common import log as logging
from eon.virt import constants
from eon.virt.kvm import driver
from eon.virt.rhel.validator import RHELValidator

LOG = logging.getLogger(__name__)


class RHELDriver(driver.KVMDriver):

    def __init__(self):
        super(RHELDriver, self).__init__()

    def pre_activation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        rhel_validator = RHELValidator(resource_inventory)
        rhel_validator.preactivation_check()

    def run_wipe_disks(self, hux_obj, resource_id):
        extra_args = {"extraVars": {
            "automate": "yes"
        }}
        LOG.warn("Wiping out secondary disks")
        hux_obj.run_playbook_by_ids('wipe_disks', resource_id,
                                    extra_args=extra_args)
        LOG.info("Secondary disks successfully wiped out")

    def modify_marker_to_skip_disk_config(self, remote_connection,
                                          action=None):
        if action == "create":
            LOG.debug("Creating marker file to skip_disk_config")
            remote_connection.exec_command_and_wait(
                constants.MKDIR_MARKER_PARENT_DIR,
                raise_on_exit_not_0=True)
            remote_connection.exec_command_and_wait(
                constants.CREATE_SKIP_DISK_CONFIG_MARKER,
                raise_on_exit_not_0=True)
            LOG.debug("Marker file skip_disk_config created successfully")
        elif action == "delete":
            LOG.debug("Deleting marker file to skip_disk_config")
            remote_connection.exec_command_and_wait(
                constants.DELETE_SKIP_DISK_CONFIG_MARKER,
                raise_on_exit_not_0=True)
            LOG.debug("Marker file skip_disk_config deleted successfully")
        else:
            pass
