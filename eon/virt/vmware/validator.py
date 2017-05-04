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

import re

from eon.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class ESXValidator():

    def __init__(self, cluster_data):
        self.cluster_data = cluster_data

    def validate_names(self):
        regex_for_space = '.*\s+.*'
        regex_for_special_chars = "^[a-zA-Z0-9_-]*$"
        cluster_name = self.cluster_data.get("name")
        dc_name = self.cluster_data.get(
                  "inventory").get("datacenter").get("name")
        if (re.match(regex_for_space, cluster_name) or
            re.match(regex_for_space, dc_name) or
            not re.search(regex_for_special_chars, cluster_name) or
            not re.search(regex_for_special_chars, dc_name)):
            error_msg = (_("Either the name of cluster(%s) or its "
                        "datacenter(%s) contains whitespace or special "
                       "character, Supported characters include "
                        "alphanumeric characters, '_' and '-'. "
                        "Rename it and retry activation"
                         ) % (cluster_name, dc_name))
            log_error_msg = (("Either the name of cluster(%s) or its "
                        "datacenter(%s) contains whitespace or special "
                       "character, Supported characters include "
                        "alphanumeric characters, '_' and '-'. "
                        "Rename it and retry activation"
                         ) % (cluster_name, dc_name))
            LOG.error(log_error_msg)
            raise Exception(error_msg)

    def check_cluster_hosts(self):
        hosts_count = len(self.cluster_data.get("inventory").get("hosts"))
        cluster_name = self.cluster_data.get("name")
        if hosts_count == 0:
            error_msg = (_("Cluster %s does not have any host "
                         "associated with it") % cluster_name)
            log_error_msg = (("Cluster %s does not have any host "
                         "associated with it") % cluster_name)
            LOG.error(log_error_msg)
            raise Exception(error_msg)

    def check_DRS_enabled(self):
        cluster_name = self.cluster_data.get("name")
        if not self.cluster_data.get("inventory").get("DRS"):
            error_msg = (("Cluster %s does not have any host "
                         "associated with it") % cluster_name)
            LOG.error(error_msg)
            raise Exception(_("DRS not enabled for cluster %s") % cluster_name)

    def check_instances(self):
        hosts = self.cluster_data.get("inventory").get("hosts")
        for host_id in hosts:
            if host_id['vms'] > 0:
                error_msg = ("Virtual machine instances are "
                             "running on the compute node")
                LOG.warn(error_msg)

    def validate_cluster(self):
        self.validate_names()
        self.check_cluster_hosts()
        self.check_DRS_enabled()
        self.check_instances()
