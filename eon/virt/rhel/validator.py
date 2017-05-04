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

import os
import configparser
import re
from eon.common.ssh_utilities import RemoteConnection
from eon.virt import constants as kvm_constants
from eon.openstack.common import log as logging
from eon.common import exception
from eon.common.exception import PreActivationCheckError
from eon.virt.kvm import validator


LOG = logging.getLogger(__name__)


class RHELValidator(validator.KVMValidator):

    def __init__(self, data):
        self.data = data
        self.remote_connection = RemoteConnection(self.data.get("ip_address"),
                                                  self.data.get("username"),
                                                  self.data.get("password"))

    def _verify_subscription_yum_repo_disabled(self):
        activation_msg = ('Verifying if the Red Hat Subscription Manager '
                            'repository is disabled in KVM compute: %s' %
                          (self.data.get("ip_address")))
        error_msg = (_('The Red Hat Subscription Manager repository is not '
                       'disabled in KVM compute: %s') %
                     (self.data.get("ip_address")))
        log_error_msg = (('The Red Hat Subscription Manager repository '
                       'is not disabled in KVM compute: %s') %
                     (self.data.get("ip_address")))
        corrective_action = ('Disable the Red Hat Subscription Manager '
                               'repository in KVM compute: %s' %
                             (self.data.get("ip_address")))
        LOG.info(activation_msg)
        config_obj = configparser.ConfigParser()
        tmp_path = val = None
        try:
            tmp_path = self.remote_connection.get(
                kvm_constants.SUBSCRIPTION_REPO_PATH)
            with open(tmp_path) as fp:
                config_obj.readfp(fp)
            val = config_obj.get("main", "enabled")
        except Exception as exc:
            LOG.exception(exc)
            err_msg = (_("Could not verify if the subscription repo is "
                       "disabled. %s" % exc))
            log_err_msg = (("Could not verify if the subscription repo is "
                       "disabled. %s" % exc))
            LOG.error(log_err_msg)
            raise PreActivationCheckError(err=err_msg)

        finally:
            if tmp_path:
                os.remove(tmp_path)

        if val == "1":
            LOG.error(log_error_msg)
            LOG.warn(corrective_action)
            raise PreActivationCheckError(err=error_msg)

    def _check_compute_node_kernel_version(self):
        activation_msg = ('Verifying correct kernel version on remote host')
        error_msg = (_('Unsupported kernel version on remote host %s') %
                     (self.data.get("ip_address")))
        log_error_msg = (('Unsupported kernel version on remote host %s') %
                     (self.data.get("ip_address")))
        corrective_action = ('Consult the HP Helion CloudSystem Installation'
                               ' and Configuration Guide for'
                               ' supported hypervisors')
        LOG.info(activation_msg)
        try:
            cmd = kvm_constants.CHECK_KERNAL_VERSION
            exit_code, out, err = self.remote_connection.exec_command_and_wait(
                cmd,
                raise_on_exit_not_0=True)
            # Checking for RHEL7
            pattern = kvm_constants.CHECK_KERNAL_VERSION_PATTERN_RHEL7
            if re.match(pattern, out.rstrip()) is None:
                raise PreActivationCheckError(err=error_msg)
        except exception.RhelCommandNoneZeroException as rh_ex:
            LOG.exception(rh_ex)
            LOG.error(log_error_msg)
            LOG.warn(corrective_action)
            raise PreActivationCheckError(err=error_msg)
        except Exception as exc:
            error_msg = (_("Coudldn't verify kernel version on remote host %s")
                         % (self.data.get("ip_address")))
            log_msg = (("Coudldn't verify kernel version on remote host %s")
                         % (self.data.get("ip_address")))
            LOG.error(log_msg)
            LOG.exception(exc)
            raise PreActivationCheckError(err=error_msg)

    def preactivation_check(self):
        self._verify_subscription_yum_repo_disabled()
        self._check_compute_node_kernel_version()
        self.check_instances()
