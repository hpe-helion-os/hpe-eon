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

from eon.deployer import basedriver
from eon.deployer import util
from eon.deployer.computeproxy import compute_proxy_vm
from eon.deployer import constants
from eon.deployer.computeproxy import cp_utility

from oslo_config import cfg

CONF = cfg.CONF


class ProxyInstaller(basedriver.BaseDriver):
    """
    Base class for proxy installer
    """
    def __init__(self):
        super(ProxyInstaller, self).__init__()

    def setup_network(self, data):
        proxy_utility = cp_utility.ProxyInstallerUtility(data)
        return proxy_utility.create_network_infrastructure()

    def create(self, data):
        proxy_utility = cp_utility.ProxyInstallerUtility(data)
        if CONF.network.esx_network_driver == constants.NOOP_NETWORK_DRIVER:
            proxy_utility.configure_network_infrastructure()
        session = self._get_session(data)
        proxy_vm_name = self._get_proxy_vm_name(data)
        proxy_info = compute_proxy_vm.create_shell_vm(
            session, proxy_vm_name, data)
        return proxy_info

    def get_info(self, data):
        session = self._get_session(data)
        proxy_vm_name = self._get_proxy_vm_name(data)
        conf_pg_name = self._get_conf_pg_name(data)
        return compute_proxy_vm.get_shell_vm_info(
            session, proxy_vm_name, conf_pg_name)

    def delete(self, data):
        session = self._get_session(data)
        proxy_vm_name = self._get_proxy_vm_name(data)
        conf_pg_name = self._get_conf_pg_name(data)
        compute_proxy_vm.delete_shell_vm(session, proxy_vm_name,
                                         conf_pg_name)

    def delete_template(self, data):
        session = self._get_session(data)
        content = session.get('content')
        template_name = self._get_template_name(data)
        vm = content.rootFolder.find_by_name(template_name)
        if not vm:
            return

        compute_proxy_vm.delete_vm(vm, session['si'])

    def teardown_network(self, data):
        proxy_utility = cp_utility.ProxyInstallerUtility(data)
        return proxy_utility.teardown_network(data)

    def _get_session(self, data):
        session = dict()
        vc = data.get("vcenter_configuration")
        si = util.VMwareUtils.get_vcenter_session(
            vc['ip_address'], vc['port'],
            vc['username'], vc['password'])
        session['si'] = si
        session['content'] = si.RetrieveContent()
        return session

    def _get_proxy_vm_name(self, data):
        vc = data.get("vcenter_configuration")
        cluster_name = vc.get("cluster")
        dc_name = vc.get("datacenter")
        return "_".join(['novaproxy', dc_name, cluster_name])

    def _get_template_name(self, data):
        vm_config = util.get_vmconfig_input(
            data, constants.PROXY_KEY,
            net_driver=CONF.network.esx_network_driver)
        return vm_config.get("template_name")

    def _get_conf_pg_name(self, data):
        vm_config = util.get_vmconfig_input(
            data, constants.PROXY_KEY,
            net_driver=CONF.network.esx_network_driver)
        conf_network = util.get_conf_pg(data, vm_config)
        return conf_network.get('name')
