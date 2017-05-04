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

import logging
import time

from oslo_vmware import exceptions as vmware_excep

from eon.openstack.common.gettextutils import _
from eon.virt.vmware import constants
from eon.virt.vmware import vim_util as v_util


MAX_OBJECTS = 500
NOT_AUTHENTICATED = "NotAuthenticated"
INVALID_COLLECTOR = "InvalidCollectorVersion"
LOG = logging.getLogger(__name__)


class VCInventoryCollector(object):
    def __init__(self, vc_data, session, threadPool):
        self._vcenter_data = vc_data
        self.session = session
        self._inventory = {}
        self._pool = threadPool
        self.vim = self.session.vim
        self.monitor = True

    def register_managed_objects(self, vc_data):

        t = time.time()
        clus_inventory = v_util.retreive_vcenter_inventory(self.vim)
        try:
            for obj in clus_inventory:
                if hasattr(obj, 'propSet'):
                    self._inventory[(obj.obj._type, obj.obj.value)] = (
                        self.convert_propset_to_dict(obj.propSet))
                else:
                    LOG.debug("Unable to retrieve propSet for %s. "
                                % str(obj))
                    if hasattr(obj, 'missingSet'):
                        # The object may have information useful for logging
                        for m in obj.missingSet:
                            LOG.warning(("Unable to retrieve value for "
                                         "%(path)s. Reason: %(reason)s"),
                                        {'path': m.path,
                                         'reason': m.fault.localizedMessage})
        except Exception as e:
            LOG.exception('Error while retrieving vCenter Inventory, Error: '
                         '%s', e)

        LOG.info('vCenter Inventory retrieved in %s seconds' % (
            str(time.time() - t)))

        if clus_inventory:
            v_util.create_filter(self.vim)
            self._pool.spawn_n(self.monitor_property_updates)

    def get_cluster_by_name(self, cluster_name):
        cluster_mors = filter(lambda x: x[0] == "ClusterComputeResource",
                              self._inventory)

        for x in cluster_mors:
            if self._inventory[x]["name"] == cluster_name:
                return x

    def get_cluster_by_moid(self, cluster_moid):
        cluster_mors = filter(lambda x: x[0] == "ClusterComputeResource",
                              self._inventory)

        for x in cluster_mors:
            if x[1] == cluster_moid:
                return x

    def is_cluster_inside_folder(self, clus_mor):
        """
        Check whether the cluster is inside folders
        """
        folder_mors = filter(lambda x: x[0] == "Folder", self._inventory)
        LOG.debug("Checking whether the cluster is inside a folder,"
                  "Folder MORs: %s" % folder_mors)
        parent_moid = self._inventory[clus_mor]['parent'].value
        for folder in folder_mors:
            _i, moid = folder
            if moid == parent_moid:
                # Find the dc for the folder
                dc_mors = filter(lambda x: x[0] == "Datacenter",
                                 self._inventory)
                LOG.debug("datacenter MORS %s" % str(dc_mors))
                # Check if the clusters parent matches any datacenter
                # if if matches, deduce its not there under any folder
                for dc in dc_mors:
                    hostFolder = self._inventory[dc]['hostFolder']
                    if hostFolder.value == moid:
                        return False

        LOG.warning(("Cluster %s is inside a folder."
                     " so it will be ignored. If you want to activate"
                     " the cluster, remove from the"
                     " folder and try again") % str(clus_mor))
        return True

    def get_cluster_names(self, ignore_clusters_in_folders=False):
        """
        :return: list of tuples ex :[(domain-c1, cluster_name)]
        """
        cluster_mors = filter(lambda x: x[0] == "ClusterComputeResource",
                              self._inventory)

        cluster_names = []
        for cls_mor in cluster_mors:
            if (ignore_clusters_in_folders and
                self.is_cluster_inside_folder(cls_mor)):
                continue

            cluster_names.append((cls_mor[1],
                                  self._inventory[cls_mor]["name"]))

        return cluster_names

    def get_datacenter_for_cluster_name(self, cluster_name):
        cluster = self.get_cluster_by_name(cluster_name)
        return self.get_datacenter_for_cluster(cluster)

    def get_datacenter_for_cluster_moid(self, cluster_moid):
        cluster = self.get_cluster_by_moid(cluster_moid)
        return self.get_datacenter_for_cluster(cluster)

    def get_datacenter_for_cluster(self, cluster):
        folder_mors = filter(lambda x: x[0] == "Folder", self._inventory)
        parent_moid = self._inventory[cluster]['parent'].value
        for folder in folder_mors:
            obj_type, moid = folder
            if moid == parent_moid:
                # Find the dc for the folder
                dc_mors = filter(lambda x: x[0] == "Datacenter",
                                 self._inventory)
                dc = None
                dc_moid = None
                for dc in dc_mors:
                    dc_type, dc_moid = dc
                    hostFolder = self._inventory[dc]['hostFolder']
                    if hostFolder.value == moid:
                        break

                return {'moid': dc_moid,
                        'name': self._inventory[dc]['name']
                }

    def get_vc_inventory(self):
        data_center = {}
        dc_mors = filter(lambda x: x[0] == "Datacenter",
                         self._inventory)
        cluster_mors = filter(lambda x: x[0] == "ClusterComputeResource",
                              self._inventory)
        for cluster_mor in cluster_mors:
            # cluster_mor is a tuple with type and moid.
            cluster_moid = cluster_mor[1]
            cluster_name = self._inventory[cluster_mor]["name"]
            dc = self.get_datacenter_for_cluster(cluster_mor)
            dc_moid = dc['moid']
            if not data_center.get(dc_moid):
                data_center[dc_moid] = {}
                data_center[dc_moid]['clusters'] = {}

            data_center[dc_moid]['name'] = dc['name']
            data_center[dc_moid]['clusters'][cluster_moid] = cluster_name

        # Finds the clusters count per dataCenter.
        for key in data_center:
            data_center[key]["clusters_count"] = len(data_center
                                                     [key]["clusters"].keys())

        data_center['count'] = len(dc_mors)
        return data_center

    def get_vcenter_inventory(self):
        return self._inventory

    def get_hosts_by_cluster_moid(self, cluster_moid):
        """
        :param cluster_name: name of the cluster
        :param vc_hosts_mors: managed objects of all the hosts in vcenter
        :return:
        """
        host_mors = filter(lambda x: x[0] == "HostSystem", self._inventory)

        cluster_host_mors = []
        for x in host_mors:
            if (self._inventory[x]["parent"].value ==
                cluster_moid):
                cluster_host_mors.append(x)

        return cluster_host_mors

    def get_hosts_for_cluster(self, cls_moid):
        result = {}
        result["hosts"] = []
        host_mors = self.get_hosts_by_cluster_moid(cls_moid)
        for host in host_mors:
            _, host_moid = host
            host_details = {}
            host_details['name'] = self._inventory[host]['name']
            host_details['connection_state'] = \
                self._inventory[host]['runtime.connectionState']
            host_details["moid"] = host_moid
            vms = 0
            try:
                vm_array_obj = self._inventory[host]['vm']
                vms = len(vm_array_obj.ManagedObjectReference)
            except Exception:
                # Indicates no VMs are present
                vms = 0
            host_details['vms'] = vms
            result['hosts'].append(host_details)

        return result

    def get_cluster_spec_inventory(self, cluster_moid):
        """
        : returns
        {
        "moid": ,
        "datacenter":
            {"moid": "dc=1",
             "name": "asd",
            },
        "hosts":
            [{
            }],
        ""
        }
        """
        inventory = {}
        cls_mor = None
        cluster_mors = filter(lambda x: x[0] == "ClusterComputeResource",
                              self._inventory)

        for cluster_mor in cluster_mors:
            if cluster_mor[1] == cluster_moid:
                cls_mor = cluster_mor
                break

        if not cls_mor:
            return {}
        dc = self.get_datacenter_for_cluster(cls_mor)
        inventory["datacenter"] = dc
        inventory.update(self.get_hosts_for_cluster(cluster_moid))
        inventory["DRS"] = (self._inventory[cls_mor]["configurationEx"]
                            .drsConfig.enabled)

        return inventory

    def wait_for_inventory(self):
        return self.monitor

    def _reset_inventory(self):
        """
        Resets the inventory and creates
        session
        """
        self.version = ""
        self.session._create_session()
        v_util.create_filter(self.vim)

    def monitor_property_updates(self):
        """
        Waits for updates from vCenter and handles the cache
        """
        LOG.info("Started monitor updates")
        self.version = ""
        while self.wait_for_inventory():
            try:
                updateSet = None
                LOG.debug("Waiting for inventory updates on vCenter: %s. "
                          % (self._vcenter_data['ip_address']))

                updateSet = v_util.wait_for_updates_ex(self.vim,
                                                       self.version)
                if not updateSet:
                    continue

                current_version = updateSet.version
                if current_version != self.version:
                    self._updated_changed_properties(updateSet)
                    self.version = current_version
                    LOG.debug("Update version on vCenter (%s) %s" % (
                        self._vcenter_data['ip_address'], self.version))
                    time.sleep(20)

            except vmware_excep.VimConnectionException as e:
                LOG.error("Connection to vCenter failed."
                          " Retrying...")
                self._reset_inventory()

            except vmware_excep.VimFaultException as excep:
                # If this is due to an inactive session, we should re-create
                # the session and retry.
                if (NOT_AUTHENTICATED in excep.fault_list or
                    INVALID_COLLECTOR in excep.fault_list):
                    # in activate session creating new
                    self._reset_inventory()
            except Exception, e:
                LOG.error(("Exception while waiting for updates on vCenter."
                           "Error : %s") % e)
                time.sleep(constants.VCENTER_RECONNECT_INTERVAL)

        LOG.info(_("Stopped monitoring for vCenter updates"))
        self.session.logout()

    def _updated_changed_properties(self, updateSet):
        if not updateSet:
            return
        else:
            pfus = updateSet.filterSet
            for propertyfilterupdate in pfus:
                ous = propertyfilterupdate.objectSet
                for objectupdate in ous:
                    if objectupdate.kind == "enter"\
                            or objectupdate.kind == "modify":
                        self._handle_add_event(objectupdate,
                                               updateSet.version)
                    elif objectupdate.kind == "leave":
                        self._handle_delete_event(objectupdate)

    def _handle_add_event(self, objectupdate, version):
        vc_inv = self._inventory
        mor = objectupdate.obj
        changeSet = objectupdate.changeSet
        for propertychange in changeSet:
            if propertychange.op == 'add'\
                    or propertychange.op == 'assign':
                if hasattr(propertychange, "name"):
                    if str(version) is not "0_1":
                        LOG.debug(('Update received on vCenter %s'
                                   ' for MOR %s with property %s'
                                   ' and type %s')
                                 % (self._vcenter_data['ip_address'],
                                    (mor._type, mor.value),
                                    propertychange.name, propertychange.op))
                    prop_name = propertychange.name
                    prop_val = getattr(propertychange, "val", 0)
                    if (mor._type, mor.value) in vc_inv.keys():
                        vc_inv[(mor._type, mor.value)][prop_name] = prop_val
                    else:
                        vc_inv[(mor._type, mor.value)] = {prop_name: prop_val}

    def _handle_delete_event(self, objectupdate):
        mor = objectupdate.obj
        LOG.info(('Delete event received on vCenter %(vcenter)s'
                   'for MOR %(mor)s' %
                   {'vcenter': self._vcenter_data['ip_address'],
                    'mor': (mor._type, mor.value)}))
        if (mor._type, mor.value) in self._inventory.keys():
            self._inventory.pop((mor._type, mor.value))

    def convert_propset_to_dict(self, propset_list):
        propset_dict = {}
        for prop in propset_list:
            propset_dict[prop.name] = prop.val
        return propset_dict
