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

import contextlib
import eventlet
import mock
import time
import uuid

from testtools import TestCase
from eon.virt.vmware.inventory_collector import VCInventoryCollector
from eon.virt.vmware import vim_util as v_util
from eon.tests.unit import fake_data


class ManagedObject(object):

    """Managed Data Object base class."""

    def __init__(self, name="ManagedObject", obj_ref=None):
        """Sets the obj property which acts as a reference to the object."""
        super(ManagedObject, self).__setattr__('objName', name)
        if obj_ref is None:
            obj_ref = str(uuid.uuid4())
        object.__setattr__(self, 'obj', self)
        object.__setattr__(self, 'propSet', [])
        object.__setattr__(self, 'value', obj_ref)
        object.__setattr__(self, '_type', name)

    def set(self, attr, val, op):
        """
        Sets an attribute value. Not using the __setattr__ directly for we
        want to set attributes of the type 'a.b.c' and using this function
        class we set the same.
        """
        self.__setattr__(attr, val, op=op)

    def get(self, attr):
        """
        Gets an attribute. Used as an intermediary to get nested
        property like 'a.b.c' value.
        """
        return self.__getattr__(attr)

    def __setattr__(self, attr, val, op=None):
        for prop in self.propSet:
            if prop.name == attr:
                prop.val = val
                return
        elem = Prop()
        elem.name = attr
        elem.val = val
        elem.op = op
        self.propSet.append(elem)

    def __getattr__(self, attr):
        for elem in self.propSet:
            if elem.name == attr:
                return elem.val
        msg = _("Property %(attr)s not set for the managed object %(name)s")
        raise AttributeError(msg % {'attr': attr, 'name': self.objName})


class Prop(object):
    """Property Object base class."""

    def __init__(self):
        self.name = None
        self.val = None


class ClusterComputeResource(ManagedObject):

    def __init__(self, **kwargs):
        super(ClusterComputeResource, self).__init__("ClusterComputeResource",
                                                     "domain-c1999")
        self.set("name", "esx-app-cluster2", "add")


class DataObject(object):
    pass


class FolderObject(DataObject):

    def __init__(self, value):
        super(FolderObject, self).__init__()
        self.value = value


class FakeVim(object):

    def __init__(self):
        pass

    def wait_for_updates_ex(self, version, update_kind, collector=None,
                            max_wait=85,
                            max_update_count=-1):
        args = []
        kwargs = {'version': version, 'collector': collector,
                  'max_wait': max_wait, 'max_udate_count': max_update_count}

        return self._wait_for_updates("DummyAttribute", update_kind,
                                      *args, **kwargs)

    def _get_cluster_properties(self, op, name, val):
        prop = DataObject()
        prop.op = op
        prop.name = name
        prop.val = val
        return prop

    def _wait_for_updates(self, method, update_kind, *args, **kwargs):
        version = kwargs.get("version")
        if not version:
            updateSet = DataObject()
            updateSet.version = 1
            filterSet = []
            updateSet.filterSet = filterSet
            propFilterUpdate = DataObject()
            filterSet.append(propFilterUpdate)
            objectSet = []
            propFilterUpdate.objectSet = objectSet
            objectUpdate = DataObject()
            cluster_compute = ClusterComputeResource()
            objectUpdate.obj = cluster_compute
            objectUpdate.kind = update_kind
            changeSet = []
            for prop in cluster_compute.propSet:
                changeSet.append(prop)
            objectUpdate.changeSet = changeSet
            objectSet.append(objectUpdate)
            return updateSet
        else:
            time.sleep(0)
            return None


class TestVCInventoryCollector(TestCase):

    def setUp(self):
        super(TestVCInventoryCollector, self).setUp()
        drs_mock = mock.Mock()
        drs_mock.drsConfig.enabled = True
        self._pool = mock.MagicMock()
        self.pool = eventlet.GreenPool()
        self.vcdata = {"ip_address": "192.168.1.3",
                       'username': 'user',
                       'password': 'password'}
        self.session = mock.MagicMock()
        self.vc_inv = VCInventoryCollector(self.vcdata, self.session,
                                           self._pool)
        self.vc_inv._inventory = \
            {('ClusterComputeResource', "domain-c1997"):
                {'name': "esx-app-cluster", "parent":
                    FolderObject("folder-12")},
             ('ClusterComputeResource', "domain-1"):
                {'name': "esx-app-cluster1", "parent":
                    FolderObject("folder-13"),
                    'configurationEx': drs_mock},
             ('Folder', "folder-12"): {'mor': "folder-12"},
             ('Folder', "folder-13"): {'mor': "folder-13"},
             ('HostSystem', 'host-21'): {'name': "10.10.0.1"},
             ('Datacenter', 'datacenter-21'): {'hostFolder':
                                                FolderObject("folder-12"),
                                               'name': "datacenter-21"},
            }
        self.vc_inv2 = VCInventoryCollector(self.vcdata, self.session,
                                           self._pool)
        self.vc_inv2._inventory = \
            {('ClusterComputeResource', "domain-c1997"):
                {'name': "esx-app-cluster", "parent":
                    FolderObject("folder-12")},
             ('ClusterComputeResource', "domain-c1998"):
                {'name': "esx-app-cluster1", "parent":
                    FolderObject("folder-13")},
             ('Folder', "folder-12"): {'mor': "folder-12"},
             ('Folder', "folder-13"): {'mor': "folder-13"},
             ('HostSystem', 'host-21'): {'name': "10.10.0.1"},
             ('Datacenter', 'datacenter-21'): {'hostFolder':
                                                FolderObject("folder-12"),
                                               'name': "datacenter-21"}
            }

    def test_get_datacenter_for_cluster_name(self):
        expected = {'moid': 'datacenter-21',
                        'name': 'datacenter-21'
                    }
        self.assertEqual(self.vc_inv.
                            get_datacenter_for_cluster_name('esx-app-cluster'),
                         expected)

    def test_get_datacenter_for_cluster_moid(self):
        expected = {'moid': 'datacenter-21',
                        'name': 'datacenter-21'
                    }
        self.assertEqual(self.vc_inv.
                            get_datacenter_for_cluster_moid('domain-c1997'),
                         expected)

    def test_get_cluster_names_ignore_folders(self):
        expected = [('domain-c1997', 'esx-app-cluster')]
        self.assertEqual(self.vc_inv.
                            get_cluster_names(True),
                         expected)

    def test_get_cluster_names(self):
        expected = [('domain-c1997', 'esx-app-cluster'),
                    ('domain-c1998', 'esx-app-cluster1')]
        self.assertEqual(self.vc_inv2.
                            get_cluster_names(False),
                         expected)

    def test_get_vc_inventory(self):
        expected = {'count': 1, 'datacenter-21': {'clusters':
                                      {'domain-c1997': 'esx-app-cluster',
                                       'domain-c1998': 'esx-app-cluster1'
                                      },
                                    'clusters_count': 2,
                                    'name': 'datacenter-21'}}
        self.assertEqual(self.vc_inv2.get_vc_inventory(), expected)

    def test_register_managed_objects(self):
        with contextlib.nested(
            mock.patch.object(v_util, "retreive_vcenter_inventory"),
            mock.patch.object(v_util, "create_filter"),
            ):
            self.vc_inv.register_managed_objects(self.vcdata)

    def mock_ret_true(self):
        yield True
        yield False

    def test_monitor_property_updates(self):
        fake_vim = FakeVim()
        with contextlib.nested(
            mock.patch.object(v_util, "wait_for_updates_ex"),
            mock.patch.object(v_util, "create_filter"),
            mock.patch.object(self.vc_inv, "wait_for_inventory"),
            mock.patch.object(time, "sleep")
            ) as (wait_for_updates, _, ret_true, _):
            ret_true.side_effect = self.mock_ret_true()
            wait_for_updates.return_value = fake_vim.wait_for_updates_ex(None,
                                                                    "enter")
            self.vc_inv.monitor_property_updates()

    def test_monitor_property_updates_leave(self):
        fake_vim = FakeVim()
        with contextlib.nested(
            mock.patch.object(v_util, "wait_for_updates_ex"),
            mock.patch.object(v_util, "create_filter"),
            mock.patch.object(self.vc_inv, "wait_for_inventory"),
            mock.patch.object(time, "sleep")
            ) as (wait_for_updates, _, wait_for, _):
            wait_for.side_effect = self.mock_ret_true()
            wait_for_updates.return_value = fake_vim.wait_for_updates_ex(None,
                                                                    "leave")
            self.vc_inv.monitor_property_updates()

    def test_get_vcenter_inventory(self):
        self.assertEqual(self.vc_inv.get_vcenter_inventory(),
                         self.vc_inv._inventory)

    def test_get_cluster_spec_inventory(self):
        cluster_moid = "domain-1"
        with contextlib.nested(
            mock.patch.object(self.vc_inv, "get_datacenter_for_cluster"),
            mock.patch.object(self.vc_inv, "get_hosts_for_cluster")
            ) as (get_dc, get_host):
            get_dc.return_value = {}
            expected = {'datacenter': {}, 'DRS': True}
            self.assertEqual(expected,
                        self.vc_inv.get_cluster_spec_inventory(cluster_moid))
            get_dc.assert_called_once_with(("ClusterComputeResource",
                                            "domain-1"))
            get_host.assert_called_once_with(cluster_moid)

    def test_get_cluster_spec_inventory_with_non_existent_moid(self):
        cluster_moid = "domain-112"
        expected = {}
        self.assertEqual(expected,
                        self.vc_inv.get_cluster_spec_inventory(cluster_moid))

    def test_get_hosts_for_cluster(self):
        host_mors = [("HostSystem", fake_data.host_moid1)]
        with mock.patch.object(self.vc_inv, "get_hosts_by_cluster_moid") \
            as get_host:
            self.vc_inv._inventory = fake_data.sample_inventory
            get_host.return_value = host_mors
            observed = self.vc_inv.get_hosts_for_cluster(
                fake_data.cluster_moid1)
            self.assertEqual(fake_data.host_fake_inv_data1, observed)

    def test_get_hosts_for_cluster_with_vms(self):
        host_mors = [("HostSystem", fake_data.host_moid1)]
        with mock.patch.object(self.vc_inv, "get_hosts_by_cluster_moid") \
            as get_host:
            self.vc_inv._inventory = fake_data.sample_inventory_with_vms
            get_host.return_value = host_mors
            observed = self.vc_inv.get_hosts_for_cluster(
                fake_data.cluster_moid1)
            self.assertEqual(fake_data.host_fake_inv_data1, observed)
            get_host.assert_called_once_with(fake_data.cluster_moid1)

    def test_get_hosts_by_cluster_moid(self):
        self.vc_inv._inventory = fake_data.sample_inventory
        self.assertEqual([],
                self.vc_inv.get_hosts_by_cluster_moid(
                fake_data.cluster_moid1))
