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
import json

import eon.db
import requests
from eon.common import exception
from eon.common.constants import ResourceConstants as res_const
from eon.deployer import driver as net_driver
from eon.deployer import constants as deployer_const
from eon.openstack.common import log as logging
from eon.openstack.common import lockutils
from eon.common import context as eon_context
from eon.virt import driver, constants
from eon.virt.vmware import constants as vmware_const, utils
from eon.virt.vmware import hlm_input_model
from eon.virt.vmware import vcenter_manager
from eon.virt.vmware.constants import (CLUSTER_DVS_MAPPING,
                                       NOOP_NETWORK_DRIVER,
                                       OVSVAPP_NETWORK_DRIVER)
from eon.virt.vmware import network_prop_json_handler
from eon.virt.vmware import validator
from eon.virt.common import utils as vir_utils
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.hlm_facade import constants as facade_constants
from eon.hlm_facade import exception as facade_excep
from webob import exc as web_exc
from oslo_config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class VMwareVCDriver(driver.ResourceDriver):

    def __init__(self):
        self.vcm = vcenter_manager.vCenterManager()
        self.db_api = eon.db.get_api()
        self.db_api.setup_db_env()
        self.hux_obj = None

    def get_properties(self, data):
        return data

    def validate_create(self, context, create_data):
        return self.vcm.add_vcenter(create_data)

    def monitor_events(self, vc_data):
        self.vcm.monitor_events(vc_data)

    def validate_update(self, update_data, data):
        if self.vcm.get_session(update_data):
            return self.vcm.update_vcenter(update_data, data)

    def validate_delete(self, vc_data):
        self.vcm.delete_vcenter(vc_data)

    def auto_import_resources(self, context, db_vc_data,
                       db_vc_rsrcs, db_vc_rscrc_prop):
        (new_clusters, removed_clusters) = self.vcm.poll_vcenter_resources(
                                               db_vc_data, db_vc_rsrcs,
                                               db_vc_rscrc_prop)
        for cluster in new_clusters:
            self._import_cluster(context, cluster,
                                        db_vc_data['id'])

        clusters_id_mappings = self._get_cluster_id_mapping(db_vc_rsrcs,
                                                    db_vc_rscrc_prop)
        for cluster in removed_clusters:
            self._unimport_cluster(context, cluster, clusters_id_mappings)

    def _import_cluster(self, context, resource, resource_mgr_id):
        LOG.info("Import cluster %s " % resource[1])
        try:
            db_session = self.db_api.get_transactional_session(
                'Import-Cluster')

            data = {'resource_mgr_id': resource_mgr_id,
                    'ip_address': "UNSET",
                    'username': "UNSET",
                    'password': "UNSET",
                    'type': constants.EON_RESOURCE_TYPE_ESX_CLUSTER,
                    'state': constants.EON_RESOURCE_STATE_IMPORTED,
                    'port': "UNSET",
                    'name': resource[1]}
            create_ref = self.db_api.create_resource(context,
                                              data,
                                              session=db_session)
            self.db_api.create_property(context,
                                        create_ref.id,
                                        constants.CLUSTER_MOID,
                                        resource[0],
                                        session=db_session)
            LOG.info("Imported cluster %s and id is %s"
                      % (resource[1], create_ref.id))
            self.db_api.commit_session('Import-Cluster', db_session)

        except Exception as e:
            message = ("Failed to import cluster. Error: %s") % e.message
            LOG.warn(message)
            self.db_api.rollback_session('Import-Cluster', db_session)

    def _unimport_cluster(self, context, remove_cluster,
                          clusters_id_mappings):
        LOG.info("Un-Import Cluster %s " % remove_cluster[0])
        try:
            for cluster_id in clusters_id_mappings:
                if cluster_id[1] == remove_cluster[0]:
                    LOG.info("Deleting cluster %s" % cluster_id[0])
                    self.db_api.delete_resource(context, cluster_id[0])
        except Exception as e:
            msg = "Failed to delete cluster %s. Error: %s" % (
                                                cluster_id, e.message)
            LOG.info(msg)

    def _get_cluster_id_mapping(self, db_vc_resources,
                                 db_vc_resources_prop):
        cluster_ids = []
        cluster_rscrs = [db_resource for db_resource in db_vc_resources
                         if db_resource['type'] == "esxcluster"]
        for cluster_rscr in cluster_rscrs:
            cluster_props = db_vc_resources_prop[cluster_rscr['id']]
            for cluster_prop in cluster_props:
                if (cluster_prop["key"] == constants.CLUSTER_MOID):
                    cluster_ids.append((cluster_rscr['id'],
                                        cluster_prop["value"]))
        return cluster_ids

    def get_inventory(self, vcenter_data):
        vcdata = {}
        vc_data = {}
        vc_inv = self.vcm.get_vcenter_inventory_collector(vcenter_data)
        if vc_inv:
            vc_data = vc_inv.get_vc_inventory()

        vc_data = {'datacenter': vc_data}
        vcdata['resources'] = vc_data
        return vcdata

    def get_res_inventory(self, res_mgr_data, res_property_obj):
        """
        :param res_mgr_data: resource mangager DB object
        :param res_property_obj: property DB object
        """
        vc_inv = self.vcm.get_vcenter_inventory_collector(res_mgr_data)
        clus_data = {}
        if vc_inv:
            cluster_moid = self.get_resource_property(res_property_obj,
                                                      constants.CLUSTER_MOID)
            clus_data = vc_inv.get_cluster_spec_inventory(cluster_moid)
        return clus_data

    def populate_network_json(self, context, data):
        return network_prop_json_handler.populate_network_properties(context,
                                                                     data)

    def get_network_properties(self, context, vc_data, cluster_data):
        """
        Gets the network_properties from the DB per datacenter.
        """
        cluster_inventory = cluster_data['inventory']
        network_prop = self.get_cluster_network_properties(context,
            cluster_data["id"])
        if network_prop:
            return network_prop
        else:
            return self.get_dc_network_properties(
                context, vc_data["id"],
                cluster_inventory.get('datacenter')["name"])

    def get_cluster_network_properties(self, context, cluster_id):
        try:
            network_prop = self.db_api.get_properties(context,
                            cluster_id,
                            key=vmware_const.NET_PROPS)[0]
        except exception.NotFound:
            return

        if network_prop:
            return json.loads(network_prop.value)

    def get_dc_network_properties(self, context, id_, dc_name):
        try:
            network_prop = self.db_api.get_resource_mgr_properties(
                                        context, id_,
                                        dc_name)[0]
            if network_prop:
                return json.loads(network_prop.value)

        except exception.NotFound:
            return

    def store_network_dc_level(self, context, cluster_data, dc_name,
                               network_prop, session):
        """Stores in DB
        """
        vc_data = cluster_data['resource_manager_info']
        dc_network_prop = self.get_dc_network_properties(context,
                                    vc_data['id'], dc_name)
        if dc_network_prop:
            self.db_api.update_resource_mgr_property(
                context, "update", vc_data['id'], dc_name,
                json.dumps(network_prop),
                session=session)
        else:
            self.db_api.create_resource_mgr_property(
                                        context,
                                        vc_data['id'],
                                        dc_name,
                                        json.dumps(network_prop),
                                        session=session)

    def _store_and_setup_network(self, context,
            resource_type, cluster_data,
            network_prop, store_dc_level=False, set_network=False):
        resource_id = cluster_data["id"]
        dc_name = cluster_data.get('inventory').get('datacenter')["name"]
        db_session = self.db_api.get_transactional_session('set-network')
        try:
            if set_network:
                vc_dict = copy.deepcopy(cluster_data['resource_manager_info'])
                network_driver = net_driver.load_resource_network_driver(
                    resource_type)
                network_input_data = utils.frame_network_data(
                                             vc_dict,
                                             network_prop,
                                             dc_name)
                network_driver.setup_network(network_input_data)
                if CONF.network.esx_network_driver == NOOP_NETWORK_DRIVER:
                    proxy_driver = net_driver.load_resource_compute_driver(
                        resource_type)
                    proxy_input_data = copy.deepcopy(network_input_data)
                    proxy_driver.setup_network(proxy_input_data)

            if store_dc_level:
                self.store_network_dc_level(context,
                                            cluster_data, dc_name,
                                            network_prop, db_session)

            # store at cluster level
            self.db_api.create_property(context, resource_id,
                                        vmware_const.NET_PROPS,
                                        json.dumps(network_prop),
                                        session=db_session)
            self.db_api.commit_session('set-network', db_session)

        except Exception:
            self.db_api.rollback_session('set-network', db_session)
            raise

    @lockutils.synchronized("set-network-lock")
    def set_network_properties(self, context, resource_type,
                               cluster_data,
                               network_prop):
        """Sets the network properties for the cluster / datacenter
        based on the input for activation.
        if activation_in_progress_for_dc and network_prop:
            @with_lock:
                store_in_cluster_level
                set up network

        if not activation_in_progress_for_dc:
            if network_prop:
                @with_lock:
                    store in dc_level in res_mgr_property if empty
                    store_in_cluster_level in property
                    setup network
            else:
                get dc_network_prop
                if not dc:
                    raise error
        """
        if (cluster_data.get("state") ==
            constants.RESOURCE_STATE_ACTIVATION_INITIATED):
            return
        if (self.activation_in_progress_per_dc(context, cluster_data) and
            network_prop):
            self._store_and_setup_network(context,
                                          resource_type,
                                          cluster_data,
                                          network_prop,
                                          set_network=True)

        elif not self.activation_in_progress_per_dc(context, cluster_data):
            if network_prop:
                self._store_and_setup_network(context,
                                          resource_type,
                                          cluster_data,
                                          network_prop,
                                          store_dc_level=True,
                                          set_network=True)
            else:
                network_prop = self.get_network_properties(context,
                    cluster_data['resource_manager_info'], cluster_data)
                if not network_prop:
                    raise Exception(_("Network information is neither passed "
                                      "nor present"))

        elif (self.activation_in_progress_per_dc(context, cluster_data) and
              not network_prop):
            LOG.info("Network properties are not passed, assuming the network"
                     " is set up.")
            network_prop = self.get_network_properties(context,
                cluster_data['resource_manager_info'], cluster_data)

        LOG.info("[%s] Network configurations completed successfully"
                 % cluster_data["id"])
        return network_prop

    def _delete_and_teardown_network(self, context, cluster_data,
                                     network_property,
                                     delete_cluster_level=False,
                                     delete_dc_level=False,
                                     tear_down_network=False):

        dc_data = cluster_data.get('inventory').get('datacenter')
        vc_data = cluster_data['resource_manager_info']

        if tear_down_network:
            vc_dict = copy.deepcopy(cluster_data['resource_manager_info'])
            data_nw_driver = utils.frame_network_data(
                                vc_dict, network_property,
                                dc_data['name'])

            network_driver = net_driver.load_resource_network_driver(
                cluster_data["type"])

            try:
                network_driver.teardown_network(data_nw_driver)
                if CONF.network.esx_network_driver == NOOP_NETWORK_DRIVER:
                    proxy_driver = net_driver.load_resource_compute_driver(
                        cluster_data["type"])
                    data_proxy_driver = copy.deepcopy(data_nw_driver)
                    proxy_driver.teardown_network(data_proxy_driver)

            except Exception as e:
                err_msg = ('Failed to delete the DVS and Portgroups'
                            ' for datacenter %s: %s' % (dc_data['name'], e))
                LOG.error(err_msg)

        try:
            if delete_dc_level:
                self.db_api.delete_resource_mgr_property(context,
                                            vc_data['id'],
                                            dc_data['name'])

        except exception.NotFound as e:
            LOG.error(e)

        try:
            if delete_cluster_level:
                self.db_api.delete_property(context,
                                            cluster_data["id"],
                                            vmware_const.NET_PROPS)
        except exception.NotFound as e:
            LOG.error(e)

    @lockutils.synchronized("set-network-lock")
    def delete_network_properties(self, context, cluster_data):
        """
        if last_cluster:
            delete_cluster_level
            delete_dc_level
            tear down network
        else:
            if cluster prop exists:
                delete_cluster_level
                tear down network
            else:
                don't do anything
        """
        delete_cluster_level = True
        delete_dc_level = False
        teardown_network = True

        if self.is_last_cluster_per_dc(context, cluster_data):
            network_prop = self.get_network_properties(context,
                            cluster_data['resource_manager_info'],
                            cluster_data)
            delete_dc_level = True

        else:
            network_prop = self.get_cluster_network_properties(context,
                                                    cluster_data["id"])

            dc_network_prop = self.get_network_properties(context,
                cluster_data['resource_manager_info'],
                cluster_data)

            # (NOTE) if the DC specific network is equal to that of
            # clusters, and there are clusters which are not in imported
            # state, we want to avoid deleting the dvSwitches
            if cmp(network_prop["portGroups"],
                dc_network_prop["portGroups"]) == 0 and (
                cmp(network_prop["switches"],
                    dc_network_prop["switches"]) == 0):
                teardown_network = False

        if not network_prop:
            LOG.warn('Network properties for not set, nothing to clean'
                ' up')
            return

        self._delete_and_teardown_network(context, cluster_data,
            network_prop, delete_cluster_level=delete_cluster_level,
            delete_dc_level=delete_dc_level,
            tear_down_network=teardown_network)

    def activation_in_progress_per_dc(self, context, cluster_data):
        """
        Checks for any activation of clusters in progress for the DataCenter
        :return: True if activated/activating/etc clusters are found
        """
        return self._check_for_active_clusters(context, cluster_data)

    def is_last_cluster_per_dc(self, context, cluster_data):
        """
        returns True if the given cluster is the last cluster in the
        eon inventory.
        That is, all the clusters are in imported/removing/removed state.
        """
        return not self._check_for_active_clusters(context, cluster_data,
            expected_state=constants.EXPECTED_STATE)

    def _check_for_active_clusters(self, context, cluster_data,
                                   expected_state=constants.EXPECTED_STATE):
        """
        Checks for any imported or activated clusters in the datacenter
        in vcenter
        :return: True if activated clusters are found
        """
        vc_data = cluster_data[res_const.RESOURCE_MANAGER_INFO]
        datacenter_inventory = cluster_data['inventory']['datacenter']
        vc_inventory = self.get_inventory(vc_data)
        dc_data = vc_inventory.get("resources").get("datacenter")
        dc_data.pop('count')
        clusters_dict = dc_data.get(datacenter_inventory.get('moid')). \
                                                    get('clusters')

        db_clusters = self.db_api.get_all_resources(
                                context,
                                resource_mgr_id=vc_data['id'])
        for db_cluster in db_clusters:
            if db_cluster['name'] == cluster_data.get("name"):
                continue

            if (db_cluster['name'] in clusters_dict.values() and
                    db_cluster.get('state') in expected_state):
                LOG.debug('Activated/Provisioning clusters are found'
                          ' in datacenter %s.' % datacenter_inventory['name'])
                return True
        LOG.debug('No activated/imported clusters found in datacenter %s'
                  % datacenter_inventory['name'])
        return False

    def _update_state(self, context, rsrc_id, state):
        values = {'state': state}

        self.db_api.update_resource(
                context,
                rsrc_id,
                values)

    def host_commission(self, context, resource_type, cluster_data,
                        network_prop):
        vc_data = cluster_data['resource_manager_info']
        provision_data = utils.frame_provision_data(vc_data, cluster_data,
                                                    network_prop)
        provision_data_net = copy.deepcopy(provision_data)
        network_driver = net_driver.load_resource_network_driver(
                                                    resource_type)
        try:
            self._update_state(context, cluster_data["id"],
                               constants.RESOURCE_STATE_HOST_COMMISSIONING)
            network_info = network_driver.create(provision_data_net)
            LOG.info("[%s] Network info %s" % (cluster_data["id"],
                      network_info))

            if not network_info:
                raise Exception(_("Unable to provision OVSvAPP."
                                " Check whether the new host is added to the "
                                "cluster and is in maintenance mode"))

            # this checks for the net_info status from ovsvapp installer
            new_hosts_list = utils.process_ovsvapp_network_info(
                                        network_info.get(cluster_data["name"]))

            hlm_prop = self.db_api.get_properties(context,
                                 cluster_data['id'],
                                 res_const.HLM_PROPERTIES)
            hlm_info = json.loads(hlm_prop[0].value)
            LOG.info("hlm properties %s" % logging.mask_password(hlm_info))
            host_ovsvapp_list = hlm_info[vmware_const.NETWORK_DRIVER].get(
                cluster_data["name"])
            host_ovsvapp_list.extend(new_hosts_list)
            LOG.info("Updated hlm properties %s" % hlm_info)
            self.db_api.update_property(context,
                                    "update-property",
                                    cluster_data['id'],
                                    res_const.HLM_PROPERTIES,
                                    json.dumps(hlm_info))
            return new_hosts_list

        except Exception as e:
            LOG.exception(('Exception occurred while provisioning'
                          ' ovsvapp %s') % str(e))
            self._update_state(context, cluster_data["id"],
                               constants.EON_RESOURCE_STATE_ACTIVATED)
            raise e

    def host_commission_model_changes(self, context, id_, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        hosts_data = kwargs.get('hosts_data')
        payload_data = kwargs.get('payload_data')
        LOG.info("[%s] Building the input model data" % id_)
        input_model_for_hosts = self.build_input_model_data_for_new_hosts(
            context,
            resource_inventory,
            hosts_data,
            payload_data)
        LOG.info("[%s] Input model for new hosts %s"
                 % (id_, input_model_for_hosts))
        self._update_state(context, id_,
                           constants.EON_RESOURCE_STATE_ACTIVATING)
        with lockutils.lock("run-playbook"):
            self.hux_obj = HLMFacadeWrapper(context)
            self._update_input_model(id_, input_model_for_hosts)
            self._invoke_activate_playbooks(context, id_,
                                            input_model_for_hosts,
                                            True)

    def move_hosts(self, id_, cluster_data, hosts_data, rollback=False):
        """
        Invokes the script to put the host back to the cluster in case of
        success or moves to maintenance mode in case of failure
        :param cluster_data:
        :param hosts_data: [{"host_name": <esx_host_name>,
                           "status": "success/failed"}]
        """
        vcenter_details = cluster_data[constants.RSRC_MGR_INFO]
        data = {"vcenter_host": vcenter_details.get('ip_address'),
                "vcenter_username": vcenter_details.get('username'),
                "vcenter_password": vcenter_details.get('password'),
                "vcenter_https_port": vcenter_details.get('port'),
                }

        for host in hosts_data:
            data["host_name"] = host.get('esx_hostname')
            # in case of rollback, we need to set the status failed
            if rollback:
                data["status"] = deployer_const.HOST_COMM_FAILURE
            else:
                data["status"] = host.get('status')
                LOG.info('[%s] Triggering the call to move back the '
                         'commissioned host %s to cluster' %
                         (id_, data.get('esx_hostname')))

            network_driver = net_driver.load_resource_network_driver(
                                                    cluster_data["type"])
            LOG.info("Host info %s" % logging.mask_password(data))
            network_driver.update(data)

    def roll_back_host_info(self, context, current_hosts_list, cluster_data):
        """
        :param current_hosts_list [{'name': 1}, {'name': 2}]
        """
        hlm_prop = self.db_api.get_properties(context,
                                 cluster_data['id'],
                                 res_const.HLM_PROPERTIES)
        hlm_info = json.loads(hlm_prop[0].value)
        host_ovsvapp_list = hlm_info[vmware_const.NETWORK_DRIVER].get(
            cluster_data["name"])

        new_list = utils.strip_current_ovsvapp_host_info(current_hosts_list,
                                                         host_ovsvapp_list)

        hlm_info[vmware_const.NETWORK_DRIVER][cluster_data["name"]] = new_list

        LOG.info("Updated hlm properties %s" % hlm_info)
        self.db_api.update_property(context,
                                "update-property",
                                cluster_data['id'],
                                res_const.HLM_PROPERTIES,
                                json.dumps(hlm_info))

    def provision(self, context, resource_type, cluster_data, network_prop):
        """
        Brings up the proxy VMs [ovsvpp and compute VM] for clusters
        """
        if (cluster_data.get("state") ==
            constants.RESOURCE_STATE_ACTIVATION_INITIATED):
            LOG.info("Resource %s is already provisioned, nothing to do"
                     % cluster_data["id"])
            return

        self._update_state(context, cluster_data['id'],
                           constants.EON_RESOURCE_STATE_PROVISIONING)
        vc_data = cluster_data['resource_manager_info']
        provision_data = utils.frame_provision_data(vc_data, cluster_data,
                                                    network_prop)
        provision_proxy_data = copy.deepcopy(provision_data)
        provision_network_data = copy.deepcopy(provision_data)
        provision_data_delete = copy.deepcopy(provision_data)
        clus_data_delete = copy.deepcopy(cluster_data)
        network_driver = net_driver.load_resource_network_driver(resource_type)
        compute_driver = net_driver.load_resource_compute_driver(resource_type)
        try:
            network_info = network_driver.create(provision_network_data)
            compute_info = compute_driver.create(provision_proxy_data)
            if not (compute_info and network_info):
                return
            compute_info.update({vmware_const.CLUSTER_MOID:
                                utils.get_cluster_property(
                                    cluster_data, vmware_const.CLUSTER_MOID)})
            hlm_info = {vmware_const.ESX_PROXY_NAME: compute_info,
                        vmware_const.NETWORK_DRIVER: network_info}
            self.db_api.create_property(context,
                                    cluster_data['id'],
                                    res_const.HLM_PROPERTIES,
                                    json.dumps(hlm_info))
            self._update_state(context, cluster_data['id'],
                           constants.EON_RESOURCE_STATE_PROVISIONED)
        except Exception as e:
            LOG.exception('Exception %s occurred provisioning'
                          ' resource proxies %s. Initiate Rollback action'
                          % (e, cluster_data['name']))
            exception_type = e.__class__.__name__
            if exception_type == 'ProxyException':
                LOG.error('Compute proxy VM failed to configure.'
                          ' Going to delete the network proxy VMs')
                network_driver.delete(provision_data_delete)
            elif exception_type == 'OVSvAppException':
                LOG.error('OVSvApp VMs failed to configure')
            self.delete_network_properties(context,
                                           clus_data_delete)
            raise e

    def remove(self, context, resource_type, cluster_data):
        """
        deletes the service VMs
        """
        network_driver = net_driver.load_resource_network_driver(resource_type)
        compute_driver = net_driver.load_resource_compute_driver(resource_type)
        vc_data = cluster_data['resource_manager_info']
        try:
            network_prop = self.get_network_properties(context,
                                                       vc_data,
                                                       cluster_data)
            provision_data = utils.frame_provision_data(vc_data, cluster_data,
                                                        network_prop)
            provision_proxy_data = copy.deepcopy(provision_data)
            provision_data_delete = copy.deepcopy(provision_data)
            compute_driver.delete(provision_proxy_data)
            network_driver.delete(provision_data_delete)

            is_upload_to_cluster = network_prop.get(
                "template_info", {}).get(vmware_const.UPLOAD_TO_CLUSTER)

            # (NOTE) Need to call network_driver when different templates are
            # used. Calling only compute_driver for now since it will always
            # be present.
            if is_upload_to_cluster:
                compute_driver.delete_template(provision_proxy_data)
            else:
                if self.is_last_cluster_per_dc(context, cluster_data):
                    compute_driver.delete_template(provision_proxy_data)

        except Exception as e:
            LOG.exception(e)
            exception_type = e.__class__.__name__
            if exception_type == 'ProxyException':
                LOG.error('Failed to delete Compute proxy VM')
                network_driver.delete(provision_data_delete)
            elif exception_type == 'OVSvAppException':
                LOG.error('Failed to delete OVSvApp VMs')
        finally:
            # deleting from Resource properties table
            self.db_api.delete_property(context, cluster_data['id'],
                                        res_const.HLM_PROPERTIES)

            # (NOTE) Not raising the exception here, since we want to clean up
            # everything, If we raise exception here, manager wont be able
            # to rest of the clean up.

    def rollback_activate(self, context, cluster_data):
        # Setting state to provisioned to prevent cleanup of
        # proxy and ovsvapp vms
        self._update_state(context, cluster_data['id'],
                           constants.EON_RESOURCE_STATE_PROVISIONED)
        return True

    def _build_servers_info(self, context, action, cluster_data_list,
                            input_model_data):
        servers = []
        for cluster_data in cluster_data_list:
            hlm_prop = self.db_api.get_properties(context,
                                 cluster_data['id'],
                                 res_const.HLM_PROPERTIES)
            hlm_prop_value = json.loads(hlm_prop[0].value)
            (proxy_info, nw_node_info) = (hlm_input_model.
                            build_servers_info(hlm_prop_value, action,
                                               cluster_data,
                                               input_model_data))
            servers.append(proxy_info)
            for node_info in nw_node_info:
                servers.append(node_info)
        return {"servers": servers}

    def _build_passthrough_info(self, context, action, cluster_data_list):
        passthrough_info = []
        global_passthrough_info = []
        for cluster_data in cluster_data_list:
            hlm_prop = self.db_api.get_properties(context,
                                 cluster_data['id'],
                                 res_const.HLM_PROPERTIES)
            hlm_prop_value = json.loads(hlm_prop[0].value)
            (proxy_passth_info, nw_node_passth_info) = (hlm_input_model.
                                        build_passthrough_info(hlm_prop_value,
                                                               cluster_data))
            passthrough_info.append(proxy_passth_info)
            for node_info in nw_node_passth_info:
                passthrough_info.append(node_info)

            # Frame global section - required in a migrated environment
            global_passthrough_info.append(
                cluster_data[res_const.RESOURCE_MANAGER_INFO])

        return {"pass-through": {"servers": passthrough_info,
                                 "global": {"vmware": global_passthrough_info}
                                 }}

    def build_input_model_data(self, context, action, cluster_data_list,
                               input_model_data=None):
        """
        returns:
        {
        servers: {servers: [{server1}, {server2}]}
        pass_through: {pass-through: [{passthrough1}, {passthrough2}]}
        }
        """
        input_model = {}
        # Build data to update in servers yaml
        servers = self._build_servers_info(context, action,
                                           cluster_data_list,
                                           input_model_data)
        input_model["servers"] = servers

        # Build data to update in passthrough yaml
        passthrough_info = self._build_passthrough_info(context,
                                                        action,
                                                        cluster_data_list)
        input_model["pass_through"] = passthrough_info
        return input_model

    def build_input_model_data_for_new_hosts(self, context,
            cluster_data, ovsvspp_list, input_model_data=None):
        """
        :param ovsvspp_list : [{'status': 'success', 'host-moid': u'host-459',
            'ovsvapp_node': 'ovsvapp-10-1-221-78'}, {}]
        :returns
        {
        servers: {servers: [{server1}, {server2}]}
        pass_through: {pass-through: [{passthrough1}, {passthrough2}]}
        }
        """
        servers_info = []
        passthrough_info = []
        input_model = {}
        hlm_prop = self.db_api.get_properties(context,
                                 cluster_data['id'],
                                 res_const.HLM_PROPERTIES)
        hlm_prop_value = json.loads(hlm_prop[0].value)
        cluster_dvs_mapping = hlm_prop_value.get(
            vmware_const.NETWORK_DRIVER).get(CLUSTER_DVS_MAPPING)
        global_passthrough_info = [cluster_data[
                                       res_const.RESOURCE_MANAGER_INFO]]

        for ovsvapp_dict in ovsvspp_list:
            nw_node_info = hlm_input_model._build_network_driver_info(
                                            [ovsvapp_dict],
                                            constants.INPUT_MODEL_ADD,
                                            cluster_data, input_model_data)

            LOG.info("network node info %s" % nw_node_info)
            nw_node_passth_info = (
                hlm_input_model._build_ovsvapp_passthrough_info(
                                        [ovsvapp_dict], cluster_data,
                                        cluster_dvs_mapping))

            LOG.info("OVSvApp pass through info %s" % nw_node_passth_info)

            for node_info in nw_node_info:
                servers_info.append(node_info)

            for node_info in nw_node_passth_info:
                passthrough_info.append(node_info)

        # Frame global section - required for Host commissioning in a
        # migrated environment
        input_model["pass_through"] = {"pass-through": {
            "servers": passthrough_info,
            "global": {"vmware": global_passthrough_info}}
        }
        input_model["servers"] = {"servers": servers_info}
        return input_model

    def pre_activation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        if (resource_inventory.get("state") ==
            constants.EON_RESOURCE_STATE_PROVISIONED):
            return
        data = kwargs.get('data')
        id_ = resource_inventory.get("resource_mgr_id")
        dc_name = (resource_inventory.get("inventory")
                   .get("datacenter").get("name"))
        if not data:
            net_prop = self.get_dc_network_properties(context, id_,
                                                       dc_name)
            if not net_prop:
                msg = (_("config json parameter not found"
                         " for ESX cluster activation"))
                id_ = resource_inventory.get("id")
                raise exception.ActivationFailure(resource_name=id_,
                                                   err=msg)
        val = validator.ESXValidator(resource_inventory)
        val.validate_cluster()

    def get_hypervisor_hostname(self, resource_inventory):
        domain_id = None
        for res_dic in resource_inventory[constants.EON_RESOURCE_META_KEY]:
            if res_dic.get("name") == constants.CLUSTER_MOID:
                domain_id = res_dic['value']
        vcenter_id = resource_inventory.get("resource_mgr_id")
        if domain_id is None or vcenter_id is None:
            raise exception.HostnameException(
                                resource_name=resource_inventory['id'],
                                err=_("Either domain_id or "
                                "vcenter_id is None"))
        hostname = domain_id + '.' + vcenter_id
        return hostname

    def post_activation_steps(self, context, id_, resource_inventory=None):
        hypervisor_hostname = self.get_hypervisor_hostname(resource_inventory)
        vir_utils.validate_nova_neutron_list(context, id_, self.db_api,
                                             hypervisor_hostname,
                                             None, constants.ACTIVATION,
                                             False)
        if CONF.network.esx_network_driver == OVSVAPP_NETWORK_DRIVER:
            vir_utils.check_ovsvapp_agent_list(context,
                                               hypervisor_hostname,
                                               resource_inventory)

    def pre_deactivation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        if (resource_inventory.get("state") ==
            constants.EON_RESOURCE_STATE_PROVISIONED):
            return
        hypervisor_hostname = self.get_hypervisor_hostname(resource_inventory)
        vir_utils.check_for_running_vms(self, context, hypervisor_hostname,
                                        resource_inventory)

    def post_deactivation_steps(self, context, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        hypervisor_hostname = self.get_hypervisor_hostname(resource_inventory)
        vir_utils.delete_nova_service(context, hypervisor_hostname)
        if CONF.network.esx_network_driver == OVSVAPP_NETWORK_DRIVER:
            self.delete_neutron_service(context, resource_inventory)

    def get_host_list(self, resource_inventory):
        hosts_ip_list = []
        hosts = resource_inventory.get('inventory').get('hosts')
        for ip in hosts:
            ip['name'] = unicode(ip['name'])
            hosts_ip_list.append(ip["name"])
        return hosts_ip_list

    def delete_neutron_service(self, context, resource_inventory):
        """Delete neutron-service from the controller.
        """
        agent_id = None
        neutron_url = vir_utils.get_neutron_url(context)
        neutron_agents = vir_utils.get_neutron_agent_list(self, context,
                                                          neutron_url)
        hosts_ip_list = self.get_host_list(resource_inventory)

        for host_ip in hosts_ip_list:
            for agent in neutron_agents:
                ovsvapp_host_ip = (agent.get('configurations').get(
                                    'esx_host_name'))
                if ovsvapp_host_ip:
                    agent_id = str(agent.get("id"))
                    if str(ovsvapp_host_ip) == host_ip:
                        neutron_service_url, headers = (
                            vir_utils.get_neutron_agent_rest_api(
                                            context, neutron_url, agent_id))
                        break
            else:
                LOG.warn("Deleting Neutron agent with id %s failed" % agent_id)
                return False

            LOG.info("Deleting neutron agent with id %s " % agent_id)
            response = requests.delete(neutron_service_url, headers=headers,
                                       verify=False)
            if response.status_code == web_exc.HTTPNoContent.code:
                msg = ("Deleting neutron agent with id %s through url:%s "
                       "succeeded")
                msg = msg % (agent_id, neutron_url)
                LOG.info(msg)
                return True

            log_msg = ("Deleting neutron agent with id %s "
                       "failed with status code: %d")
            log_msg = log_msg % (agent_id, response.status_code)
            LOG.warn(log_msg)
            return False

    def _update_input_model(self, id_, input_data):
        LOG.debug("Update servers and pass_through data")
        servers_data = input_data.get('servers')
        pass_through_data = input_data.get('pass_through')
        self._add_servers(id_, servers_data)
        self._update_pass_through(id_, pass_through_data)

    def _add_servers(self, id_, servers_data):
        """ Add a servers.yml entry for a new node
        :return:
        """
        '''
        - id: esx-compute-001
          ip-addr: "192.168.10.10"
          role: "ESX-COMPUTE-ROLE"
        '''
        LOG.debug("[%s] Add servers with data: %s" % (id_, servers_data))
        if servers_data:
            servers = servers_data.get('servers')
            for server in servers:
                try:
                    server_id = server.get('id')
                    self.hux_obj.update_server_by_id(server, server_id)
                except facade_excep.NotFound:
                    LOG.info('[%s] Resource with id %s not found in input'
                             ' model. Updating complete server data'
                             % (id_, server_id))
                    self.hux_obj.create_server(server)
        return servers

    def _update_pass_through(self, id_, pass_thru):
        """ Add a pass_through.yml entry for a new node
        :return:
        """
        '''
        pass-through:
            servers:
            - id: esx-compute1
              data:
                vmware:
                  vcenter_cluster: cluster1
                  vcenter_id: 2e5043fc-ae08-4707-a00b-59e383b245b6
        '''
        new_servers = []
        # pass through data from input model
        input_model_pass_through = self.hux_obj.get_pass_through()
        LOG.debug("[%s] Input model pass through data: %s"
                  % (id_, input_model_pass_through))

        # To activate a cluster or perform host commissioning in a
        # migrated environment
        # TODO: This doesn't handle migration with multiple vCenters.
        # need to update based on vCenter-ID to handle multi-vCenter migration
        if not input_model_pass_through.get('global').get('vmware'):
            for vc in (pass_thru.get('pass-through').get('global').
                       get('vmware')):
                self.update_vc_pass_through(eon_context.get_admin_context(),
                                            vc)
            input_model_pass_through = self.hux_obj.get_pass_through()
        if not input_model_pass_through.get('servers'):
            input_model_pass_through['servers'] = []
        model_pass_through_servers = input_model_pass_through.get('servers')
        # eon generated servers info in pass through data
        servers = pass_thru.get('pass-through')["servers"]

        for server in servers:
            for model_server in model_pass_through_servers:
                if server['id'] == model_server['id']:
                    model_server.update(server)
                    break
            else:
                new_servers.append(server)
        model_pass_through_servers.extend(new_servers)
        LOG.info('Update pass through with data: %s'
                 % logging.mask_password(input_model_pass_through))
        self.hux_obj.update_pass_through(input_model_pass_through)
        return input_model_pass_through

    def _delete_pass_through(self, input_data):
        """
        Delete/update a pass-through info in pass-through.yml
        :return:
        """
        LOG.debug('Delete servers info from pass through')
        # pass through data from input model
        input_model_pass_through = self.hux_obj.get_pass_through()
        servers_input_model = input_model_pass_through.get('servers')
        if not servers_input_model:
            return

        id_list = []
        for server in input_data['pass_through']['pass-through']['servers']:
            id_list.append(server['id'])
        servers = [server for server in servers_input_model
                   if server['id'] not in id_list]
        input_model_pass_through['servers'] = servers
        self.hux_obj.update_pass_through(input_model_pass_through)
        return input_model_pass_through

    def _get_host_id(self, input_model):
        servers = input_model.get('servers').get('servers')
        hosts_id = []
        for server in servers:
            hosts_id.append(server.get('id'))
        LOG.debug('Getting id of servers. Return Value: %s'
                  % hosts_id)
        return hosts_id

    def _run_cp_playbooks(self, clean=False):
        self._run_config_processor(clean=clean)
        self.hux_obj.ready_deployment()

    def _stop_compute_services(self, id_, hosts):
        try:
            LOG.debug("[%s] Invoking hlm ux APIs to stop the services"
                     " in compute proxy and ovsvapps" % id_)
            self.hux_obj.run_playbook_by_ids('hlm_stop', hosts)
            LOG.debug("[%s] Stopped the services successfully"
                      " in compute proxy and ovsvapps" % id_)
        except Exception:
            LOG.info("[%s] hlm ux APIs failed to stop the services."
                       " Ignoring the exception " % (id_))

    def _rollback_activate(self, id_, hosts, input_data):
        # Stop running services on the service VMs (hlm-stop.yml)
        self._stop_compute_services(id_, hosts)
        # TODO: Have to include /etc/hosts clean up
        try:
            self.hux_obj.revert_changes()
            # clean servers info from server yml
            for host in hosts:
                self.hux_obj.delete_server(host)
            self._delete_pass_through(input_data)

            self.hux_obj.commit_changes(
                id_, "Deactivation/Rollback ESX compute resource")
            self._run_cp_playbooks(clean=True)

        except Exception as e:
            LOG.error(e)
            LOG.info(("[%s] Error in rolling back activation"
                      " Ignoring the exception ") % id_)

    def _invoke_activate_playbooks(self, context, id_, input_data,
                                   run_monitoring_plays=True, rollback=True):
        # TODO check the flow of rollback it is must.
        LOG.debug("[%s] Invoking hlm ux APIs to update the input model" % id_)
        hosts = self._get_host_id(input_data)
        retries_count = (len(hosts) *
                         facade_constants.
                         ESX_TIMEOUT_PER_HOST / facade_constants.
                         MAX_INTERVAL) + 10
        # TODO if we want to split site.yml to optimize and to introduce states
        plays = ['site']
        try:
            self.hux_obj.commit_changes(id_, "Activate ESX compute resource")
            self._run_cp_playbooks()
            for play in plays:
                self.hux_obj.run_playbook_by_ids(play, hosts,
                                                 retries=retries_count)
            # TODO needs a relook
            if run_monitoring_plays:
                self.hux_obj.run_monitoring_playbooks()

        # TODO add custom exception for and do the necessary cleanup only
        except Exception as e:
            LOG.exception(e)
            self._rollback_activate(id_, hosts, input_data)
            raise e

    def _invoke_reconfigure_playbooks(self, context, id_, input_data,
            plays=["neutron-reconfigure", "nova-reconfigure"]):
        self.hux_obj = HLMFacadeWrapper(context)
        hosts = self._get_host_id(input_data)
        retries_count = (len(hosts) *
                         facade_constants.
                         ESX_TIMEOUT_PER_HOST / facade_constants.
                         MAX_INTERVAL) + 10
        try:
            self._run_cp_playbooks()
            for play in plays:
                self.hux_obj.run_playbook_by_ids(play, hosts,
                                                 retries=retries_count)

        except Exception as e:
            LOG.exception(e)
            raise e

    def activate(self, context, id_, activate_data, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        activation_data = kwargs.get('input_model_info')
        try:
            LOG.info("[%s] Setting up required networking for "
                         "provisioning " % id_)
            network_prop = self.set_network_properties(
                    context,
                    resource_inventory['type'],
                    resource_inventory,
                    activate_data.get('network_properties'))

            LOG.info("[%s] Provisioning service VMs " % id_)
            self.provision(context, resource_inventory['type'],
                           resource_inventory,
                           network_prop)
            LOG.info("[%s] Provisioned service VMs successfully" % id_)
        except Exception as e:
            self._update_state(context, resource_inventory["id"],
                               constants.EON_RESOURCE_STATE_IMPORTED)
            LOG.exception(e)
            raise e

        try:
            LOG.info("[%s] Activating service VMs" % id_)
            self._update_state(context, resource_inventory["id"],
                               constants.EON_RESOURCE_STATE_ACTIVATING)
            LOG.info("[%s] Building the input model data for service VMs"
                     % id_)
            # build input models pass through and servers data from
            # activation and resource inventory data
            input_data = self.build_input_model_data(
                context,
                constants.INPUT_MODEL_ADD,
                [resource_inventory],
                activation_data)
            run_playbook = kwargs.get('run_playbook')

            with lockutils.lock("run-playbook"):
                self.hux_obj = HLMFacadeWrapper(context)
                self._update_input_model(id_, input_data)
                if run_playbook:
                    self._invoke_activate_playbooks(context, id_, input_data)

            self.post_activation_steps(context, id_, resource_inventory)

            state = constants.EON_RESOURCE_STATE_ACTIVATED
        except Exception as e:
            state = constants.EON_RESOURCE_STATE_PROVISIONED
            LOG.exception(e)
            raise e
        finally:
            self._update_state(context, resource_inventory["id"], state)

    def _run_config_processor(self, clean=False):
        """Runs config_processor.yml
         with no extra args when clean is False.
         with remove_deleted_servers and free_unused_addresses set to "y"
          when clean is True"""
        extra_args = None
        if clean:
            extra_args = {
                "extraVars": {"remove_deleted_servers": "y",
                              "free_unused_addresses": "y"}
                          }
        LOG.debug("Invoking hlm ux APIs to run config processor"
                 " with extra_args = %s" % str(extra_args))
        self.hux_obj.config_processor_run(body=extra_args)
        LOG.info("Finished running config processor")

    @lockutils.synchronized("set-playbook-lock")
    def _invoke_deactivate_playbooks(self, context, id_, input_data,
                                    run_playbook,
                                    resource_inventory):
        self.hux_obj = HLMFacadeWrapper(context)
        hosts = self._get_host_id(input_data)
        # TODO check are we missing any flow
        self._rollback_activate(id_, hosts, input_data)

    def deactivate(self, context, id_, **kwargs):
        resource_inventory = kwargs.get('resource_inventory')
        force_deactivate = kwargs.get('force_deactivate')
        if (force_deactivate or resource_inventory.get("state") ==
                constants.EON_RESOURCE_STATE_DEACTIVATING):
            run_playbook = kwargs.get('run_playbook')
            LOG.info("[%s] Building the input model data" % id_)
            input_data = self.build_input_model_data(context,
                                            constants.INPUT_MODEL_REMOVE,
                                            [resource_inventory])
            self._invoke_deactivate_playbooks(context, id_, input_data,
                                            run_playbook,
                                            resource_inventory)
        LOG.info("[%s] Cleaning up service VMs " % id_)
        self.remove(context, resource_inventory['type'], resource_inventory)
        LOG.info("[%s] Deleting network configurations " % id_)
        self.delete_network_properties(context, resource_inventory)

    def update(self, context, id_, **kwargs):
        """
        Updates the servers in activated state for the resource manager
        :param context:
        :param id_: resource manager id
        :param kwargs: resource_inventory
        :return None
        :raises None
        """
        resource_inventory = kwargs.get('resource_inventory')
        LOG.info("[%s] Building the input model data" % id_)
        input_data = self.build_input_model_data(context,
                                                 constants.INPUT_MODEL_UPDATE,
                                                 resource_inventory)
        LOG.info("[%s] Invoking hlm ux APIs to update the input model" % id_)
        try:
            with lockutils.lock("run-playbook"):
                self.hux_obj = HLMFacadeWrapper(context)
                self._invoke_reconfigure_playbooks(context, id_, input_data)
            LOG.info("[%s] All the ansible playbook tasks were successful "
                     "during update" % id_)

        except Exception as e:
            LOG.exception(e)
            LOG.error("[%s] Ansible playbook execution failed during update."
                      " %s" % (id_, e.message))

        finally:
            self.db_api.update_resource_mgr_property(context,
                "update_property", id_,
                key=constants.EON_RESOURCE_STATE,
                value=constants.EON_RESOURCE_MANAGER_STATE_REGISTERED)

    def update_vc_pass_through(self, context, vcenter_details):
        """
        Update the global section in the pass_through.yml with the vCenter
        details
        """
        LOG.debug("Initialize facade client to update the pass_through.yml"
                  " with the Resource manager details")

        self.hux_obj = HLMFacadeWrapper(context)
        pass_through = self.hux_obj.get_pass_through()

        if not pass_through.get('global').get('vmware'):
            pass_through.get('global')['vmware'] = []

        pass_through_vc = pass_through.get('global').get('vmware')
        pass_through_id_list = [vc.get('id') for vc in pass_through_vc]

        vcenter_id = vcenter_details.get('id')
        vcenter_name = vcenter_details.get('name')

        task = "vCenter %s Create" % vcenter_name
        vcenter_passthrough = {
            "username": vcenter_details.get('username'),
            "ip": vcenter_details.get('ip_address'),
            "port": vcenter_details.get('port'),
            "cert_check": False,
            "password": vir_utils.get_encrypted_password(
                vcenter_details.get('password')),
            "id": vcenter_id}

        if vcenter_id in pass_through_id_list:
            task = "vCenter %s Update" % vcenter_name
            vc_old = [vc for vc in pass_through_vc
                      if vc.get('id') == vcenter_id][0]
            pass_through_vc.remove(vc_old)

        pass_through_vc.append(vcenter_passthrough)

        self.hux_obj.update_pass_through(pass_through)
        LOG.info("[%s] Updated the pass_through with details %s"
                 % (vcenter_id, logging.mask_password(pass_through)))

        self.hux_obj.commit_changes(vcenter_id, task)

    def delete_vc_pass_through(self, context, vcenter_details):
        """
        Update the global section in the pass_through.yml with the vCenter
        details
        """
        LOG.debug("Initialize facade client to delete the "
                  "Resource Manager details from the pass_through.yml")

        self.hux_obj = HLMFacadeWrapper(context)
        pass_through = self.hux_obj.get_pass_through()

        pass_through_vc = pass_through.get('global').get('vmware')

        if not pass_through_vc:
            return
        pass_through_id_list = [vc.get('id') for vc in pass_through_vc]

        vcenter_id = vcenter_details.get('id')
        task = "vCenter %s Delete" % vcenter_details.get('name')

        if vcenter_id in pass_through_id_list:
            vc_to_be_deleted = [vc for vc in pass_through_vc
                                if vc.get('id') == vcenter_id][0]
            pass_through_vc.remove(vc_to_be_deleted)

        self.hux_obj.update_pass_through(pass_through)
        LOG.info("[%s] Deleted the details from the pass_through" % vcenter_id)

        self.hux_obj.commit_changes(vcenter_id, task)
