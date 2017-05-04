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

import eon.common.log as logging
from eon.common import exception
from eon.deployer import constants
from eon.deployer.network.ovsvapp.install.dvs_adapter import DVSAdapter
from eon.deployer.util import str2list

LOG = logging.getLogger(__name__)
dvs_util = DVSAdapter()


class NetworkAdapter:
    def __init__(self, service_instance, network_folder):
        self.si = service_instance
        self.net_folder = network_folder

    def _create_dvs(self, dvs):
        dvs_name = dvs['name']
        dvs_obj = self.net_folder.find_by_name(dvs_name, constants.TYPE_DVS)
        if not dvs_obj:
            physical_nics = str2list(dvs.get('physical_nics'))
            mtu = dvs['mtu']
            if not mtu:
                mtu = 1500
            dvs_obj = dvs_util.create_dvs_skeleton(
                self.si, self.net_folder, dvs_name, physical_nics, int(mtu))
        else:
            LOG.info("Found an existing DVS '{}'".format(dvs_name))

    def _create_dvpg(self, port_groups):
        for port_group in port_groups:
            pg_name = port_group['name']
            pg = self.net_folder.find_by_name(pg_name, constants.TYPE_PG)
            dvs = self.net_folder.find_by_name(port_group['switchName'],
                                               constants.TYPE_DVS)
            if not dvs:
                # Skip OVSvApp TRUNK.
                continue
            if not pg:
                dvs_util.add_dv_port_groups(self.si, dvs, port_group)
            else:
                LOG.info("Found an existing Portgroup '{}'".format(pg_name))

    def _configure_dvs(self, dvs, hosts):
        dvs_name = dvs['name']
        dvs_obj = self.net_folder.find_by_name(dvs_name, constants.TYPE_DVS)
        if not dvs_obj:
            raise exception.OVSvAppException(
                "Couldn't find the DVS '{}'".format(dvs['name']))
        dvs_util.reconfigure_dvs(
            self.si, dvs_obj, hosts, dvs.get('physical_nics'))

    def _configure_dvpg(self, port_groups):
        for port_group in port_groups:
            pg_obj = self.net_folder.find_by_name(port_group['name'],
                                                  constants.TYPE_PG)
            dvs_obj = self.net_folder.find_by_name(port_group['switchName'],
                                                   constants.TYPE_DVS)
            dvs_util.reconfigure_dv_portgroup(
                self.si, pg_obj, dvs_obj, port_group)

    def create_dvs_portgroup(self, inputs):
        dvswitches = inputs['switches']
        port_groups = inputs['portGroups']
        for dvs in dvswitches:
            if dvs.get('physical_nics'):
                self._create_dvs(dvs)
        self._create_dvpg(port_groups)

    def configure_dvs_portgroup(self, inputs, hosts):
        dvswitches = inputs['switches']
        port_groups = inputs['portGroups']
        for dvs in dvswitches:
            if not dvs.get('physical_nics'):
                # Create OVSvApp TRUNK
                self._create_dvs(dvs)
                self._create_dvpg(port_groups)
            self._configure_dvs(dvs, hosts)
        self._configure_dvpg(port_groups)
