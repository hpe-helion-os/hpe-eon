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

from eon.common import exception
from eon.virt.common.utils import VirtCommonUtils
from eon.virt.kvm.validator import KVMValidator
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.hlm_facade import exception as facade_excep
from eon.openstack.common import log as logging
from eon.openstack.common import lockutils
from eon.virt import constants
from eon.virt import driver
from eon.virt.common import utils as vir_utils
from eon.common.ssh_utilities import RemoteConnection
import eon.db

LOG = logging.getLogger(__name__)


class KVMDriver(driver.ResourceDriver):

    def __init__(self):
        self.virt_utils = VirtCommonUtils()
        self.db_api = eon.db.get_api()
        self.db_api.setup_db_env()

    def validate_create(self, context, create_data):
        validator = KVMValidator(create_data)
        validator.validate_ssh_connection()
        # Add state to PROVISIONED
        create_data[constants.EON_RESOURCE_STATE] = (
            constants.EON_RESOURCE_STATE_PROVISIONED)
        return create_data

    def validate_update(self, context, db_resource_data, update_data):
        validator = KVMValidator(update_data)
        validator.validate_ssh_connection()
        return update_data

    def validate_delete(self, data):
        state = data.get(constants.EON_RESOURCE_STATE)
        allowed_states = [constants.EON_RESOURCE_STATE_PROVISIONED]
        if state not in allowed_states:
            raise exception.InvalidStateError(observed=state,
                                              expected=allowed_states)

    def delete(self, context, id_, **kwargs):
        hux_obj = HLMFacadeWrapper(context)
        extra_args = {"extraVars": {
            "nodename": id_
        }}
        LOG.info("Deleting node %s from cobbler db" % str(id_))
        hux_obj.run_playbook('hlm_remove_cobbler_node', extra_args=extra_args)

    def _rollback_activate(self, context, hux_obj, resource_inventory,
                           run_playbook):
        resource_name = resource_inventory[constants.EON_RESOURCE_NAME]
        resource_id = resource_inventory[constants.EON_RESOURCE_ID]
        try:
            if run_playbook:
                LOG.debug("[%s] Invoking hlm ux APIs to stop the services"
                 " in compute " % resource_name)
                hux_obj.run_playbook_by_ids('hlm_stop', resource_id)
        except Exception:
            LOG.info("[%s] hlm ux APIs failed to stop the services."
                       " Ignoring the exception " % (resource_name))
        try:
            hux_obj.revert_changes()
            hux_obj.delete_server(resource_id)
            if run_playbook:
                hux_obj.commit_changes(
                    resource_id, "Deactivate/Rollback KVM compute resource")
                LOG.debug("Enabling back Password authentication")
                hux_obj.run_playbook_by_ids('hlm_post_deactivation',
                                            resource_id)
                # while deactivate free up the IP from input model and remove
                # the deleted servers
                extra_args = {"extraVars": {
                    "remove_deleted_servers": "y",
                    "free_unused_addresses": "y"}
                }
                hux_obj.config_processor_run(body=extra_args)
                hux_obj.ready_deployment()
        except Exception as e:
            LOG.error(e)
            LOG.info("[%s] Error in rolling back activation"
                       " Ignoring the exception " % (resource_name))

    def _build_input_model_data(self, context, activate_data,
                                resource_inventory):
        resource_type = resource_inventory["type"]
        try:
            input_model_data = self.virt_utils.create_servers_payload(
                    activate_data, activate_data.get('input_model'))
            input_model_data = self.virt_utils.modify_servers_payload(
                    input_model_data, resource_inventory, resource_type)
            return input_model_data
        except Exception as e:
            self.virt_utils.update_prop(context, resource_inventory['id'],
                    'state', constants.EON_RESOURCE_STATE_PROVISIONED)
            raise e

    def run_wipe_disks(self, hux_obj, resource_id):
        pass

    def modify_marker_to_skip_disk_config(self, resource_inventory,
                                          action=None):
        pass

    @lockutils.synchronized("set-playbook-lock")
    def _invoke_activate_playbooks(self, context, id_,
                                   activate_data,
                                   input_model_data,
                                   run_playbook,
                                   resource_inventory):
        resource_id = resource_inventory.get(constants.EON_RESOURCE_ID)
        hux_obj = HLMFacadeWrapper(context)
        try:
            # For pre-provisioned node, check input model data
            try:
                hux_obj.update_server_by_id(input_model_data,
                                            resource_id)
                if run_playbook:
                    hux_obj.commit_changes(
                        resource_id,
                        "Activate cobbler-provisioned KVM compute resource")
                    hux_obj.config_processor_run()
                    hux_obj.ready_deployment()
            except facade_excep.NotFound:
                LOG.error("[%s] Resource not in HLM input model. Update"
                          " with complete payload" % id_)
                # build complete input model
                input_model_data.update(
                    self.virt_utils.create_servers_payload(
                        activate_data, resource_inventory))
                # update input model
                hux_obj.create_server(input_model_data)
                if run_playbook:
                    hux_obj.commit_changes(
                        resource_id,
                        "Activate pre-provisioned KVM compute resource")
                    hux_obj.config_processor_run()
                    hux_obj.ready_deployment()
                    # Create hlmuser and copy ssh keys
                    username = resource_inventory.get(
                        constants.EON_RESOURCE_USERNAME)
                    password = resource_inventory.get(
                        constants.EON_RESOURCE_PASSWORD)
                    encrypted_password = (vir_utils
                        .get_encrypted_password(password))
                    password = (constants.DECRYPT_LOOK_UP_STR
                                 % (encrypted_password))
                    extra_args = {"extraVars": {
                        "ansible_ssh_user": username,
                        "ansible_ssh_pass": password,
                        "hlmpassword": password
                    }}
                    hux_obj.run_playbook_by_ids('hlm_ssh_configure',
                        resource_id, extra_args=extra_args)

            if run_playbook:
                skip_disk_config = activate_data.get(
                    constants.SKIP_DISK_CONFIG)
                extra_args = None
                remote_connection = RemoteConnection(
                                resource_inventory.get("ip_address"),
                                resource_inventory.get("username"),
                                resource_inventory.get("password"))
                if str(skip_disk_config).lower() == "true":
                    self.modify_marker_to_skip_disk_config(remote_connection,
                                                           action="create")
                elif str(skip_disk_config).lower() == "false":
                    self.modify_marker_to_skip_disk_config(remote_connection,
                                                           action="delete")

                    run_wipe_disks = activate_data.get(
                        constants.RUN_WIPE_DISKS, False)
                    if run_wipe_disks and \
                                    str(run_wipe_disks).lower() == "true":
                        has_os_config_ran = vir_utils.check_if_os_config_ran(
                            remote_connection)
                        if not has_os_config_ran:
                            self.run_wipe_disks(hux_obj, resource_id)
                        else:
                            LOG.warn("Skipping run wipe disks. If you need"
                                     " to force run wipe disks, delete"
                                     " the marker file %s on the compute"
                                     " node before activation." % constants.
                                     OSCONFIG_RAN_MARKER)

                hux_obj.run_playbook_by_ids('site', resource_id,
                                     extra_args=extra_args)
                hux_obj.run_monitoring_playbooks()
                self.post_activation_steps(context, id_,
                                           resource_inventory)
        except Exception as e:
            self._rollback_activate(context, hux_obj, resource_inventory,
                                    run_playbook)
            raise e

    @lockutils.synchronized("set-playbook-lock")
    def _invoke_deactivate_playbooks(self, context,
                                     run_playbook,
                                     resource_inventory):
        hux_obj = HLMFacadeWrapper(context)
        self.hypervisor_hostname = hux_obj.model_generated_host_name(
                        resource_inventory.get(constants.EON_RESOURCE_ID))
        self._rollback_activate(context, hux_obj, resource_inventory,
                           run_playbook)

    def pre_activation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        kvm_validator = KVMValidator(resource_inventory)
        kvm_validator.preactivation_check()

    def activate(self, context, id_, activate_data, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        try:
            self.virt_utils.update_prop(context, resource_inventory['id'],
                    'state', constants.EON_RESOURCE_STATE_ACTIVATING)
            LOG.info("[%s] Building the input model data" % id_)
            input_model_data = self._build_input_model_data(context,
                                                    activate_data,
                                                    resource_inventory)
            run_playbook = kwargs.get('run_playbook')
            self._invoke_activate_playbooks(context, id_,
                                            activate_data,
                                            input_model_data,
                                            run_playbook,
                                            resource_inventory)
            self.virt_utils.update_prop(context, id_,
                                        constants.EON_RESOURCE_STATE,
                                        constants.EON_RESOURCE_STATE_ACTIVATED)
        except Exception as e:
            self.virt_utils.update_prop(context, resource_inventory['id'],
                    'state', constants.EON_RESOURCE_STATE_PROVISIONED)
            raise e

    def restart_ssh_post_activation(self, remote_connection):
        remote_connection.exec_command_and_wait(
            constants.RESTART_SSH, raise_on_exit_not_0=True)

    def disable_password_auth(self, resource_inventory):
        remote_connection = RemoteConnection(
                                resource_inventory.get("ip_address"),
                                resource_inventory.get("username"),
                                resource_inventory.get("password"))
        LOG.info("Disabling password authentication on the node")
        remote_connection.exec_command_and_wait(
            constants.DISABLE_PASSWD_AUTHENTICATION,
            raise_on_exit_not_0=True)
        self.restart_ssh_post_activation(remote_connection)

    def post_activation_steps(self, context, id_, resource_inventory=None):
        hux_obj = HLMFacadeWrapper(context)
        hypervisor_hostname = hux_obj.model_generated_host_name(
                        resource_inventory.get(constants.EON_RESOURCE_ID))
        neutron_agent_type = constants.NEUTRON_AGENT_TYPE.get("kvm")
        vir_utils.validate_nova_neutron_list(context, id_, self.db_api,
                                             hypervisor_hostname,
                                             neutron_agent_type,
                                             constants.ACTIVATION)
        self.disable_password_auth(resource_inventory)

    def pre_deactivation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        hux_obj = HLMFacadeWrapper(context)
        hypervisor_hostname = hux_obj.model_generated_host_name(
                        resource_inventory.get(constants.EON_RESOURCE_ID))
        vir_utils.check_for_running_vms(self, context,
                                              hypervisor_hostname,
                                              resource_inventory)

    def deactivate(self, context, id_, **kwargs):
        self.virt_utils.update_prop(context, id_,
            'state', constants.EON_RESOURCE_STATE_DEACTIVATING)
        resource_inventory = kwargs.get('resource_inventory')
        run_playbook = kwargs.get('run_playbook')
        self._invoke_deactivate_playbooks(context, run_playbook,
                                          resource_inventory)

    def post_deactivation_steps(self, context, **kwargs):
        hypervisor_hostname = self.hypervisor_hostname
        vir_utils.delete_nova_service(context, hypervisor_hostname)
        vir_utils.delete_neutron_service(self, context, hypervisor_hostname)
