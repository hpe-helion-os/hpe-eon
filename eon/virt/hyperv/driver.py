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
from eon.openstack.common import lockutils
from eon.virt import driver
from eon.virt.common.utils import VirtCommonUtils
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.virt import constants
from eon.virt.common import utils as vir_utils
from eon.common import exception
import eon.db
from oslo_config import cfg
from eon.virt.hyperv import hyperv_utils

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
HYPERV_ROOT_ACTIONS_OPTS = [
    cfg.ListOpt('supported_os_editions',
               default=[7, 8, 12, 13, 42],
               help='Supported Hyper-V host OS editions'),
]

opt_group = cfg.OptGroup(name='HyperV_Host',
                         title='HyperV Host configuration.')
CONF.register_group(opt_group)
CONF.register_opts(HYPERV_ROOT_ACTIONS_OPTS, opt_group)


class HyperVDriver(driver.ResourceDriver):

    def __init__(self):
        super(HyperVDriver, self).__init__()
        self.virt_utils = VirtCommonUtils()
        self.db_api = eon.db.get_api()
        self.db_api.setup_db_env()
        self.hyperv_utilities = None

    def validate_update(self, context, db_resource_data, update_data):
        if not self.hyperv_utilities:
            self.hyperv_utilities = hyperv_utils.HyperVUtils(
                db_resource_data)
        self.hyperv_utilities._connectivity_check(update_data,
                                                  db_resource_data)
        return update_data

    def update(self, context, db_resource_data, id_):
        state = db_resource_data.get("state")
        if state == "activated":
            self.update_input_model(context, db_resource_data, id_)

    @lockutils.synchronized("set-playbook-lock")
    def update_input_model(self, context, resource_inventory, id_):
        resource_type = resource_inventory.get('type')
        hux_obj = HLMFacadeWrapper(context)
        try:
            input_model_data = {}
            input_model_data = self.virt_utils.modify_servers_payload(
                  input_model_data, resource_inventory, resource_type)
            hux_obj.update_server_by_id(input_model_data, id_)
            hux_obj.commit_changes(id_)
            hux_obj.config_processor_run()
            hux_obj.ready_deployment()
        except Exception as e:
            raise e

    def validate_create(self, context, create_data):
        val = vir_utils.get_global_pass_thru_data(
            context, constants.HYPERV_CLOUD)
        if not val or str(val).lower() == "false":
            message = (_("Hyper-V does not support "
                         "VxLAN or DVR network configuration"))
            raise exception.UnsupportedDeployment(msg=message)

        create_data[constants.EON_RESOURCE_STATE] = (
                                    constants.EON_RESOURCE_STATE_PROVISIONED)
        if not self.hyperv_utilities:
            self.hyperv_utilities = hyperv_utils.HyperVUtils(
                create_data)
        ip = create_data.get(constants.EON_RESOURCE_IP_ADDRESS)
        username = create_data.get(constants.EON_RESOURCE_USERNAME)
        password = create_data.get(constants.EON_RESOURCE_PASSWORD)

        if ip and username and password:
            self.hyperv_utilities._check_hyperv_host_using_pywinrm()
        return create_data

    def validate_delete(self, data):
        state = data.get(constants.EON_RESOURCE_STATE)
        allowed_states = [constants.EON_RESOURCE_STATE_PROVISIONED]
        if state not in allowed_states:
            raise exception.InvalidStateError(observed=state,
                                              expected=allowed_states)

    def post_activation_steps(self, context, id_, resource_inventory=None):
        if not self.hyperv_utilities:
            self.hyperv_utilities = hyperv_utils.HyperVUtils(
                resource_inventory)
        hypervisor_hostname = self.hyperv_utilities.get_hostname()
        neutron_agent_type = constants.NEUTRON_AGENT_TYPE.get("hyperv")
        vir_utils.validate_nova_neutron_list(context, id_, self.db_api,
                                             hypervisor_hostname,
                                             neutron_agent_type,
                                             constants.ACTIVATION)

    def _check_date_from_controller(self, collected_inventory,
                                    resource_inventory):
        host_ip = resource_inventory[constants.EON_RESOURCE_IP_ADDRESS]
        activation_msg = ("Verifying Hyper-V compute %s time with Cloud "
                          "controller" % (host_ip))
        error_msg = (_("Unable to synchronize Hyper-V compute %s time with "
                "Cloud controller") % (host_ip))
        log_error_msg = (("Unable to synchronize Hyper-V compute %s time with "
                "Cloud controller") % (host_ip))
        LOG.info(activation_msg)
        if not collected_inventory.get('host_date_configured'):
            corrective_action = ("Synchronize manually the "
                "Cloud system management appliances and HyperV compute "
                "hosts in the cluster to common ntp server")
            LOG.error(log_error_msg)
            LOG.info(corrective_action)
            raise exception.EonException(message=error_msg)

        LOG.info("Hyper-V compute %s time "
                    "is in sync with Cloud controller"
                    % (host_ip))

    def _check_csv(self, resource_inventory):
        host_ip = resource_inventory[constants.EON_RESOURCE_IP_ADDRESS]
        activation_msg = ("Validate Cluster and/or CSV")
        LOG.info(activation_msg)
        if not self.hyperv_utilities:
            self.hyperv_utilities = hyperv_utils.HyperVUtils(
                resource_inventory)
        cluster_state = self.hyperv_utilities.get_csv()
        if (cluster_state == "Standalone"):
            LOG.info("Hyper-V compute %s is not in a Cluster" % host_ip)
        elif (cluster_state == "Cluster"):
            LOG.info("Hyper-V compute %s is in a Cluster and CSV defined"
                       " is valid" % host_ip)
        elif(cluster_state):
            corrective_action = ("Manually modify  Virtual Hard disk path "
                "in Hyper-V manager to one of these " + cluster_state)
            error_msg = (_("Instance_path defined in Hyper-V manager is "
                           "not Valid CSV Path"))
            log_error_msg = (("Instance_path defined in Hyper-V manager is "
                           "not Valid CSV Path"))
            LOG.error(log_error_msg)
            LOG.info(corrective_action)
            raise exception.EonException(message=error_msg)
        else:
            corrective_action = ("Manually enable Cluster Shared Volume and"
                                   " assign to Virtual Hard disk path in "
                                   "Hyper-V manager")
            error_msg = (_("Cluster Shared volume is not enabled"))
            log_error_msg = ("Cluster Shared volume is not enabled")
            LOG.error(log_error_msg)
            LOG.info(corrective_action)
            raise exception.EonException(message=error_msg)

    def _check_for_instances(self, collected_inventory, resource_inventory):
        host_ip = resource_inventory[constants.EON_RESOURCE_IP_ADDRESS]
        activation_msg = ('Checking for instances on '
                          'the compute %s') % (host_ip)
        corrective_action = ("Manually remove these instances "
                             "using the same tools that you "
                             "used to manage the instances. "
                             "Instances consume resources and "
                             "may cause oversubscription when "
                             "not managed by HPE Helion CloudSystem")
        LOG.info(activation_msg)
        instances_count = collected_inventory.get('vm_count')
        if instances_count is not None:
            if (instances_count > 0):
                error_msg = ('Virtual machine instances count (%s) are '
                                    'running on the Hyper-V compute %s'
                                  ) % (instances_count,
                                       host_ip)
                LOG.warn(error_msg)
                LOG.warn(corrective_action)
        else:
            rst = (_("An unknown exception occurred in getting"
                     "instances count from Hyper-V compute %s."
                     "Review eon log for possible error " % host_ip))
            raise exception.WarningException(reason=rst)

    def _check_for_hyperv_version(self, collected_inventory,
                                  resource_inventory):
        host_ip = resource_inventory[constants.EON_RESOURCE_IP_ADDRESS]
        activation_msg = ('Verifying Hyper-V version and OS '
                          'edition on compute %s') % (host_ip)
        corrective_action = ('Consult the HP Helion CloudSystem '
            'Installation and Configuration Guide for '
            'supported Hyper-V versions and editions')
        _HYPERV_MAJOR_VERSION = 6
        _HYPERV_MINOR_VERSION = 3
        _HYPERV_OS_EDITIONS = {7: "Standard Server Edition",
                               8: "Datacenter Server Edition",
                               12: "Datacenter Server Core Edition",
                               13: "Standard Server Core Edition",
                               42: "Hyper-V Server"}
        LOG.info(activation_msg)
        os_version = collected_inventory.get('os_version')
        if os_version is not None:
            version = str(os_version['Major']) + "." + str(os_version['Minor'])
            if not (os_version['Major'] == _HYPERV_MAJOR_VERSION and
                    os_version['Minor'] >= _HYPERV_MINOR_VERSION):
                error_msg = ('Unsupported Hyper-V version %s on '
                            'host %s') % (version, host_ip,)
                corrective_action = ("Supported Hyper-V version is "
                                   "'WIN 2012 R2'")
                LOG.error(error_msg)
                LOG.info(corrective_action)
                raise exception.HyperVHostUnSupportedOSError()
        else:
            raise exception.EonException(
                message=(_("An unknown exception occurred getting Hyper-V "
                           "version from host %s ")) % (host_ip))

        os_edition = collected_inventory.get('os_edition')
        supported_os_editions = CONF.HyperV_Host.supported_os_editions
        if os_edition is not None:
            if os_edition['number'] not in supported_os_editions:
                error_msg = ('Unsupported OS edition %s on '
                            'Hyper-V host %s') % (os_edition['name'],
                                           host_ip,)
                corrective_action = ("Supported OS editions are %s" %
                                        _HYPERV_OS_EDITIONS.values())
                LOG.error(error_msg)
                LOG.info(corrective_action)
                raise exception.HyperVHostUnSupportedOSEditionError()
        else:
            LOG.info(corrective_action)
            raise exception.EonException(message=(_("An unknown exception "
                "occurred getting OS edition from Hyper-V "
                "host %s " % host_ip)))
        LOG.info("Hypervisor version is"
                   " %(version)s and OS edition is %(edition)s"
                   % {"version": version, "edition": os_edition['name']})

    def _check_isci_initiator_service(self, collected_inventory,
                                      resource_inventory):
        host_ip = resource_inventory[constants.EON_RESOURCE_IP_ADDRESS]
        activation_msg = ('Verifying if iSCSI Initiator service on Hyper-V'
                          ' compute %s is running' % (host_ip))
        error_msg = (_('iSCSI Initiator service is not running on Hyper-V '
                     'compute %s') % (host_ip))
        corrective_action = ('Start the iSCSI Initiator service '
                'manually on Hyper-V compute %s' % (host_ip))
        LOG.info(activation_msg)
        iSCSIState = collected_inventory.get('iSCSI_initiator_service_state')
        if not iSCSIState:
            LOG.info(corrective_action)
            raise exception.EonException(message=error_msg)

        LOG.info("Verified successfully running state of iSCSI"
        " initiator service on Hyper-V compute %s" % (host_ip))

    def _check_compute_host_name(self, collected_inventory,
                                 resource_inventory):
        host_ip = resource_inventory[constants.EON_RESOURCE_IP_ADDRESS]
        activation_msg = ('Verifying if hostname and Win32_ComputerSystem'
                          ' name are same. %s'
                        % (host_ip))
        error_msg = (_('Hostname and Win32_ComputerSystem name'
                     ' are different. %s') % (host_ip))
        corrective_action = ('Make sure that hostname is set'
                             ' to less than 15 characters %s'
                           % (host_ip))
        LOG.info(activation_msg)
        hostname = collected_inventory.get('valid_compute_name')
        if not hostname:
            LOG.info(corrective_action)
            raise exception.EonException(message=error_msg)

        LOG.info("Verified that hostname is valid  %s"
                                % (host_ip))

    def pre_activation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        if not self.hyperv_utilities:
            self.hyperv_utilities = hyperv_utils.HyperVUtils(
                resource_inventory)
        self._check_csv(resource_inventory)
        self.hyperv_utilities._check_hyperv_host_using_pywinrm()
        collected_inventory = (self.hyperv_utilities.
                               get_host_validation_data(context))
        self._check_date_from_controller(collected_inventory,
                                         resource_inventory)
        self._check_compute_host_name(collected_inventory,
                                      resource_inventory)
        self._check_for_hyperv_version(collected_inventory,
                                       resource_inventory)
        self._check_isci_initiator_service(collected_inventory,
                                           resource_inventory)
        self._check_for_instances(collected_inventory,
                                  resource_inventory)

    def _rollback_activate(self, context, hux_obj, resource_inventory,
                           run_playbook):
        resource_id = resource_inventory[constants.EON_RESOURCE_ID]
        resource_name = resource_inventory[constants.EON_RESOURCE_NAME]
        try:
            if run_playbook:
                hux_obj.run_playbook_by_ids('hlm_stop', resource_id)
        except Exception:
            LOG.info("Stopping hlm services on resource %s failed. "
                       "Ignoring the exception " % (resource_name))
        try:
            hux_obj.revert_changes()
            hux_obj.delete_server(resource_id)
            if run_playbook:
                hux_obj.commit_changes(
                    resource_id, "Deactivate/Rollback HyperV compute resource")
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
            # build complete input model
            input_model_data.update(self.virt_utils.create_servers_payload(
                                                activate_data,
                                                resource_inventory))
            return input_model_data
        except Exception as e:
            self.virt_utils.update_prop(context, resource_inventory['id'],
                    'state', constants.EON_RESOURCE_STATE_PROVISIONED)
            raise e

    @lockutils.synchronized("set-playbook-lock")
    def _invoke_activate_playbooks(self, context, id_,
                                   activate_data,
                                   input_model_data,
                                   run_playbook,
                                   resource_inventory):
        resource_id = resource_inventory[constants.EON_RESOURCE_ID]
        hux_obj = HLMFacadeWrapper(context)
        try:
            # update input model
            hux_obj.create_server(input_model_data)
            if run_playbook:
                hux_obj.commit_changes(
                    resource_id, "Activate HyperV compute resource")
                hux_obj.config_processor_run()
                hux_obj.ready_deployment()
                hux_obj.run_playbook_by_ids('site', resource_id)
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
        self._rollback_activate(context, hux_obj, resource_inventory,
                           run_playbook)

    def activate(self, context, id_, activate_data, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        try:
            self.virt_utils.update_prop(context, resource_inventory['id'],
                    'state', constants.EON_RESOURCE_STATE_ACTIVATING)
            LOG.info("[%s] Building the input model data" % id_)
            input_model_data = self._build_input_model_data(context,
                                                    activate_data,
                                                    resource_inventory)
            run_playbook = kwargs.get('run_playbook', True)
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

    def deactivate(self, context, id_, **kwargs):
        self.virt_utils.update_prop(context, id_,
            'state', constants.EON_RESOURCE_STATE_DEACTIVATING)
        resource_inventory = kwargs.get('resource_inventory')
        run_playbook = kwargs.get('run_playbook')
        self._invoke_deactivate_playbooks(context, run_playbook,
                                          resource_inventory)

    def post_deactivation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        if not self.hyperv_utilities:
            self.hyperv_utilities = hyperv_utils.HyperVUtils(
                resource_inventory)
        hypervisor_hostname = self.hyperv_utilities.get_hostname()
        vir_utils.delete_nova_service(context, hypervisor_hostname)
        vir_utils.delete_neutron_service(self, context, hypervisor_hostname)

    def pre_deactivation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        if not self.hyperv_utilities:
            self.hyperv_utilities = hyperv_utils.HyperVUtils(
                resource_inventory)
        hypervisor_hostname = self.hyperv_utilities.get_hostname()
        vir_utils.check_for_running_vms(self, context,
                                              hypervisor_hostname,
                                              resource_inventory)
