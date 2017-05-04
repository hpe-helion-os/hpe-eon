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

import copy
import eventlet
import logging
import requests
import sys
import time

from oslo_config import cfg
from oslo_vmware import api

from eon.common import exception
from eon.virt import constants as virt_constants
from eon.virt.vmware import constants
from eon.virt.vmware import inventory_collector
from eon.virt.vmware import utils


LOG = logging.getLogger(__name__)

vmwareapi_opts = [
    cfg.IntOpt('host_port',
               default=443,
               help='Port for connection to VMware VC host.'),
    cfg.IntOpt('api_retry_count',
               default=10,
               help='The number of times we retry on failures, e.g., '
                    'socket error, etc.'),
    cfg.IntOpt('task_poll_interval',
                 default=1,
                 help='The interval used for polling of remote tasks.'),
    cfg.StrOpt('wsdl_location',
               help='Optional VIM Service WSDL Location '
                    'e.g http://<server>/vimService.wsdl. '
                    'Optional over-ride to default location for bug '
                    'work-arounds')]

CONF = cfg.CONF
CONF.register_opts(vmwareapi_opts, 'vmware')

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logging.getLogger("suds.client").setLevel(logging.INFO)
LOG = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args,
                                                                 **kwargs)
        return cls._instances[cls]


class vCenterManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self._pool = eventlet.GreenPool()
        self.registered_vcenters = {}

    def get_session(self, vcenter_data):
        return VMwareAPISession(vcenter_data['ip_address'],
                                vcenter_data['username'],
                                vcenter_data['password'],
                                host_port=vcenter_data.get("port"))

    def _get_session(self, vcenter_data):
        try:
            session = None
            ipaddress = vcenter_data['ip_address']
            username = vcenter_data['username']
            password = vcenter_data['password']
            port = vcenter_data.get("port")
            _invcollector = self.get_vcenter_inventory_collector(vcenter_data)
            if _invcollector is None:
                session = VMwareAPISession(ipaddress, username, password,
                                           host_port=port)
            else:
                if _invcollector.session.is_current_session_active():
                    return _invcollector.session
                else:
                    session = VMwareAPISession(ipaddress, username, password,
                                               host_port=port)
            return session
        except Exception as e:
            msg = (_("Could not login to the vCenter server %s")
                   % (vcenter_data['ip_address']))
            LOG.exception(e)
            resolution = (_("Enter valid credentials for vCenter %s and ensure"
                            " vCenter is running and is reachable from "
                            "the controllers") % vcenter_data['ip_address'])
            raise exception.VCenterRegisterFailure(reason=msg,
                                                   resolution=resolution)

    def _get_vcenter_uuid(self, vcenter_data):
        return self._get_session(vcenter_data).vim. \
                    service_content.about.instanceUuid

    def _get_vcenter_version(self, vcenter_data):
        session = self._get_session(vcenter_data)
        vim = session.get_vim()
        about_content = vim._service_content.about
        vc_version = str(about_content.version)
        vc_build = about_content.build
        return (vc_version, vc_build, session)

    def _get_vc_creds(self, vcenter_data):
        """
        :param vcenter_data: can be a dict or DB object
        :return: a dict
        """
        if type(vcenter_data) == dict:
            return {'ip_address': vcenter_data['ip_address'],
                    'username': vcenter_data['username'],
                    'password': vcenter_data['password'],
                    'id': vcenter_data.get('id'),
                    'port': vcenter_data.get('port')
                    }
        return {'ip_address': vcenter_data.ip_address,
                'username': vcenter_data.username,
                'password': vcenter_data.password,
                'id': vcenter_data.id,
                'port': vcenter_data.port
                }

    def add_vcenter(self, vcenter_data):
        """ Add new vCenter for monitoring. """
        (vc_version, vc_build, session) = self._get_vcenter_version(
                                          vcenter_data)
        valid_flag = utils.validate_vcenter_version(vc_version, vc_build)
        if not valid_flag:
            msg = (_("VMware vCenter version (%s) and build (%s) "
                "is not supported. Please refer to the HPE Helion "
                "Support Matrix") % (vc_version, vc_build))
            log_msg = (("VMware vCenter version (%s) and build (%s) "
                "is not supported. Please refer to the HPE Helion "
                "Support Matrix") % (vc_version, vc_build))
            LOG.error(log_msg)
            raise exception.UnsupportedVCenterVersion(err=msg)
        _invcollector = inventory_collector.VCInventoryCollector(
            vcenter_data, session, self._pool)
        self.registered_vcenters[vcenter_data["ip_address"]] = _invcollector
        _invcollector.register_managed_objects(vcenter_data)
        vcenter_data.update({'id': self._get_vcenter_uuid(vcenter_data)})
        if not vcenter_data.get("port"):
            vcenter_data.update({"port": CONF.vmware.host_port})
        if not vcenter_data.get("name"):
            vcenter_data.update({"name": vcenter_data["ip_address"]})
        return vcenter_data

    def update_vcenter(self, update_data, data):
        """ Update a vCenter. """
        self.delete_vcenter(data)
        return self.add_vcenter(update_data)

    def get_vcenter_inventory_collector(self, vcenter_data):
        """Retrieve vCenter cluster inventory """
        return self.registered_vcenters.get(vcenter_data["ip_address"])

    def get_vcenter_info(self, vcenter_data):
        properties = {}
        properties['vcenter_uuid'] = self._get_vcenter_uuid(vcenter_data)
        return properties

    def _get_registered_clusters(self, db_vc_resources,
                                 db_vc_resources_prop):
        """
        :param db_vc_resources_prop : dict of prop objects
            {"1": [obj1, obj2], "2": [obj3]}
        :param db_vc_resources
        """
        clusters_list = []
        cluster_rscrs = [db_resource for db_resource in db_vc_resources
                         if db_resource['type'] == "esxcluster"]
        for cluster_rscr in cluster_rscrs:
            cluster_props = db_vc_resources_prop[cluster_rscr['id']]
            for cluster_prop in cluster_props:
                if cluster_prop["key"] == constants.CLUSTER_MOID:
                    clusters_list.append((cluster_prop['value'],
                                          cluster_rscr['name']))
        return clusters_list

    def _get_clusters_not_imported_state(self, db_vc_resources,
                                         db_vc_resources_prop):
        """
        :param db_vc_resources_prop : dict of prop objects
            {"1": [obj1, obj2], "2": [obj3]}
        :param db_vc_resources
        """
        activated_clusters = []
        cluster_rscrs = [db_resource for db_resource in db_vc_resources
                         if db_resource['type'] == "esxcluster"]
        for cluster_rscr in cluster_rscrs:
            if (cluster_rscr['state'] !=
                    virt_constants.EON_RESOURCE_STATE_IMPORTED):
                cluster_props = db_vc_resources_prop[cluster_rscr['id']]
                for cluster_prop in cluster_props:
                    if cluster_prop["key"] == constants.CLUSTER_MOID:
                        activated_clusters.append(cluster_prop["value"])
        return activated_clusters

    def poll_vcenter_resources(self, vc_data, db_vc_resources,
                               db_vc_resources_prop):
        vc_creds = self._get_vc_creds(vc_data)
        vc_inv_obj = self.get_vcenter_inventory_collector(vc_creds)
        if not vc_inv_obj:
            return ([], [])
        vc_clusters = set(vc_inv_obj.get_cluster_names(
                              ignore_clusters_in_folders=True))
        LOG.debug("Clusters present in vCenter : %s" % vc_clusters)
        if not vc_clusters:
            LOG.debug("Waiting for Inventory to be updated...")

        # Check the DB for already imported clusters
        db_clusters = set(self._get_registered_clusters(
                                                    db_vc_resources,
                                                    db_vc_resources_prop))
        LOG.debug("Registered clusters : %s", db_clusters)
        cls_not_in_imported_state = self._get_clusters_not_imported_state(
                        db_vc_resources, db_vc_resources_prop)
        added_clusters = list(vc_clusters - db_clusters)
        new_clusters = copy.deepcopy(added_clusters)
        for cluster in new_clusters:
            if cluster[0] in cls_not_in_imported_state:
                msg = _("The cluster %s is renamed and its not in 'imported'"
                        " state, Ignoring" % cluster[1])
                LOG.warn(msg)
                added_clusters.remove(cluster)

        removed_clusters = list(db_clusters - vc_clusters)
        del_clusters = copy.deepcopy(removed_clusters)
        for cluster in del_clusters:
            if cluster[0] in cls_not_in_imported_state:
                msg = _("The cluster %s is removed/renamed and it's not in "
                        "'imported' state, Ignoring" % cluster[1])
                LOG.warn(msg)
                removed_clusters.remove(cluster)
        return (added_clusters, removed_clusters)

    def monitor_events(self, vc_data):
        eventlet.spawn_n(self.update_vc_cache, vc_data)

    def update_vc_cache(self, vc_data):
        while True:
            try:
                self._update_vc_cache(vc_data)
                return
            except requests.exceptions.ConnectionError as e:
                LOG.error(e)
                LOG.error("Error while connecting registered vCenters"
                          ". Retry again in 60 seconds")
                time.sleep(60)

    def _update_vc_cache(self, vc_data):
        vc_creds = self._get_vc_creds(vc_data)
        self.add_vcenter(vc_creds)

    def logout_vc_session(self, vcenter_data):
        LOG.info("Trying log out from the vCenter %s" %
                 vcenter_data["ip_address"])
        try:
            inv_obj = self.registered_vcenters[vcenter_data["ip_address"]]
            inv_obj.monitor = False
            del self.registered_vcenters[vcenter_data["ip_address"]]
        except Exception as exc:
            LOG.warning("Failed to log out for the "
                        "vCenter: %s. Exception: %s" % (
                            vcenter_data["ip_address"], exc))

    def delete_vcenter(self, vcenter_data):
        self.logout_vc_session(vcenter_data)


class VMwareAPISession(api.VMwareAPISession):
    """Sets up a session with the VC/ESX
    """
    def __init__(self, host_ip,
                 username,
                 password,
                 host_port=None,
                 retry_count=CONF.vmware.api_retry_count,
                 scheme="https",
                 task_poll_interval=CONF.vmware.task_poll_interval,
                 wsdl_loc=CONF.vmware.wsdl_location,
                 cacert=None,
                 insecure=True):
            if not host_port:
                host_port = CONF.vmware.host_port
            else:
                host_port = int(host_port)
            super(VMwareAPISession, self).__init__(
                host_ip, username, password,
                retry_count, task_poll_interval,
                wsdl_loc=wsdl_loc,
                port=host_port,
                scheme=scheme,
                cacert=cacert,
                insecure=insecure
                )

    def _get_vim(self):
        """Create the VIM Object instance."""
        return self.vim

    def get_vim(self):
        return self._get_vim()
