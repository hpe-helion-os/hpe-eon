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
import eon.common.log as logging
from eon.deployer.network.ovsvapp.cleanup.cleanup import Cleanup
from eon.deployer.network.ovsvapp.install.network_adapter import NetworkAdapter
from eon.deployer.network.ovsvapp.install.vapp_installer import VappInstaller
from eon.deployer.network.ovsvapp.util.validate_inputs import ValidateInputs
from eon.deployer.network.ovsvapp.util.vapp_util import OVSvAppUtil
from eon.deployer.util import VMwareUtils

LOG = logging.getLogger(__name__)


class OVSvAppInstallerUtility:
    def __init__(self, input_json):
        self.input_json = input_json
        vc = self.input_json.get('vcenter_configuration')
        self.si = VMwareUtils.get_vcenter_session(
            vc['ip_address'], vc['port'], vc['username'], vc['password'])
        self.content = self.si.RetrieveContent()
        self.dc = VMwareUtils.get_data_center(
            self.content, vc['datacenter'])
        self.vc = vc

    def setup_network(self):
        ValidateInputs(self.input_json).validate_inputs(True)
        network_adapter = NetworkAdapter(self.si, self.dc['networkFolder'])
        network_adapter.create_dvs_portgroup(self.input_json)

    def invoke_ovsvapp_installer(self):
        try:
            ValidateInputs(self.input_json).validate_inputs()
            is_new_hosts = False
            ovsvapp_result = dict()
            cluster = VMwareUtils.get_cluster(
                self.content, self.dc['hostFolder'], self.vc['cluster_moid'])
            vapps = OVSvAppUtil.get_ovsvapps(
                self.content, self.dc['vmFolder'], cluster)
            vapp_hosts = vapps.keys()
            if not(len(cluster['host']) == len(vapp_hosts)):
                if vapp_hosts:
                    is_new_hosts = True
                    LOG.info("Found existing OVSvApps in cluster. OVSvApp "
                             "installer will commission the new hosts.")
                else:
                    LOG.info("No existing OVSvApps found in cluster. OVSvApp "
                             "installer will proceed for fresh activation.")
                session = dict()
                session['si'] = self.si
                session['content'] = self.content
                ovsvapp_result = VappInstaller(self.input_json).run_installer(
                    session, self.dc, cluster, vapp_hosts, is_new_hosts)
                if not ovsvapp_result:
                    raise exception.OVSvAppException(
                        _("Couldn't find any valid host for OVSvApp "
                        "installation"))
            return ovsvapp_result
        except exception.OVSvAppException as ex:
            if not is_new_hosts:
                LOG.info("Invoking cleanup script due to the error that "
                         "occurred previously.")
                Cleanup(self.input_json).unimport_cluster()
            raise ex
        except exception.OVSvAppValidationError as ev:
            LOG.exception(ev)
            raise ev
