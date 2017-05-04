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

import sqlalchemy
from oslo_config import cfg

from eon.tests.unit import test_utils_v2 as test_utils
from eon.tests.unit.db.sqlalchemy import fake_data
from eon.db.sqlalchemy import api as db_api
from eon.db.sqlalchemy import models as models
import eon.db.sqlalchemy.migration as eon_migrate
from eon.common import exception

CONF = cfg.CONF


class DbApiTestV2(test_utils.DbTestcaseV2):

    def setUp(self):
        super(DbApiTestV2, self).setUp()
        self.context = None
        self.db_api = db_api
        self.session = None
        CONF.set_default('db_auto_create', True)
        CONF.set_default('debug', True)
        self.db_api.setup_db_env()
        self.setup_sqlite(eon_migrate)

    def setup_sqlite(self, eon_migrate):
        if eon_migrate.version():
            return
        models.register_models(self.db_api.get_engine())
        eon_migrate.stamp('head')
        eon_migrate.upgrade('head')

    def test_create_rsc_mgr(self):
        rsc_mgr = self.db_api.create_resource_manager(
            self.context, fake_data.vc_data, session=self.session).to_dict()
        self._assert_rsc_mgr(rsc_mgr, fake_data.vc_data)
        self._assert_is_not_deleted(rsc_mgr)

    def test_update_rsc_mgr(self):
        rsc_mgr = self.db_api.create_resource_manager(
            self.context, fake_data.vc_data_uuid,
            session=self.session).to_dict()
        rsc_mgr_update = self.db_api.update_resource_manager(
            self.context, fake_data.vc_data_uuid.get('id'),
            fake_data.vc_data_uuid_update,
            session=self.session).to_dict()
        self._assert_rsc_mgr(rsc_mgr_update, fake_data.vc_data_uuid_update)
        self._assert_is_not_deleted(rsc_mgr)

    def test_get_all_rsc_mgr(self):
        rsc_mgr_data = self._create_rsc_mgrs()
        mgr_list = self.db_api.get_all_resource_managers(
            self.context, session=self.session, **{})

        self.assertEqual(len(mgr_list), 3)
        for mgr, mgr_data in zip(mgr_list, rsc_mgr_data):
            self._assert_rsc_mgr(mgr.to_dict(), mgr_data)
            self._assert_is_not_deleted(mgr.to_dict())

    def _create_rsc_mgrs(self):
        rsc_mgr_data = [fake_data.vc_data, fake_data.scvmm_data,
                        fake_data.vc_data1]
        self.db_api.create_resource_manager(
            self.context, rsc_mgr_data[0], session=self.session)
        self.db_api.create_resource_manager(
            self.context, rsc_mgr_data[1], session=self.session)
        self.db_api.create_resource_manager(
            self.context, rsc_mgr_data[2], session=self.session)
        return rsc_mgr_data

    def test_get_all_rsc_mgr_vcenter(self):
        self._create_rsc_mgrs()
        mgr_list = self.db_api.get_all_resource_managers(
            self.context, session=self.session, **{'type': 'vcenter'})

        self.assertEqual(len(mgr_list), 2)

    def test_get_all_rsc_mgr_scvmm(self):
        self._create_rsc_mgrs()
        mgr_list = self.db_api.get_all_resource_managers(
            self.context, session=self.session, **{'type': 'scvmm'})

        self.assertEqual(len(mgr_list), 1)

    def test_get_rsc_mgr(self):
        rsc_mgr = self.db_api.create_resource_manager(
            self.context, fake_data.vc_data, session=self.session).to_dict()
        rsc_mgr_get = self.db_api.get_resource_manager(
            self.context, rsc_mgr.get('id'), session=self.session).to_dict()
        self._assert_rsc_mgr(rsc_mgr, rsc_mgr_get)
        self._assert_rsc_mgr(fake_data.vc_data, rsc_mgr_get)

    def test_delete_rsc_mgr(self):
        rsc_mgr = self.db_api.create_resource_manager(
            self.context, fake_data.vc_data_uuid,
            session=self.session).to_dict()

        rsc_mgr_del = self.db_api.delete_resource_manager(
            self.context, rsc_mgr.get('id'), session=self.session).to_dict()

        self.assertRaises(exception.NotFound,
                          self.db_api.get_resource_manager,
                          self.context, rsc_mgr_del.get('id'),
                          session=self.session)

    def test_create_rsc_esx_cluster(self):
        self.db_api.create_resource_manager(self.context,
                                            fake_data.vc_data_uuid,
                                            session=self.session)
        rsc = self.db_api.create_resource(
            self.context, fake_data.esxclust_data,
            session=self.session).to_dict()
        self._assert_rsc_esx_cluster(rsc, fake_data.esxclust_data)
        self._assert_is_not_deleted(rsc)

    def test_create_rsc_kvm(self):
        rsc = self.db_api.create_resource(
            self.context, fake_data.rhel_data, session=self.session).to_dict()
        self._assert_rsc_kvm(rsc, fake_data.rhel_data)
        self._assert_is_not_deleted(rsc)

    def test_update_rsc(self):
        rsc = self.db_api.create_resource(
            self.context, fake_data.rhel_data, session=self.session).to_dict()
        rsc_update = self.db_api.update_resource(
            self.context, rsc.get('id'), fake_data.rhel_data_update,
            session=self.session).to_dict()
        self._assert_rsc_kvm(rsc_update, fake_data.rhel_data_update)
        self._assert_is_not_deleted(rsc)

    def _create_rscs(self):
        rsc_data = [fake_data.rhel_data, fake_data.esxclust_data,
                    fake_data.rhel_data1]
        self.db_api.create_resource_manager(
            self.context, fake_data.vc_data_uuid, session=self.session)

        self.db_api.create_resource(
            self.context, rsc_data[0], session=self.session)
        self.db_api.create_resource(
            self.context, rsc_data[1], session=self.session)
        self.db_api.create_resource(
            self.context, rsc_data[2], session=self.session)
        return rsc_data

    def test_get_all_rsc(self):
        rscs_data = self._create_rscs()
        rsc_list = self.db_api.get_all_resources(
            self.context, session=self.session, **{})

        self.assertEqual(len(rsc_list), 3)

        for rsc, rsc_data in zip(rsc_list, rscs_data):
            if rsc_data.get('type') == 'rhel':
                self._assert_rsc_kvm(rsc.to_dict(), rsc_data)
            elif rsc_data.get('type') == 'esx_cluster':
                self._assert_rsc_esx_cluster(rsc.to_dict(), rsc_data)
            self._assert_is_not_deleted(rsc.to_dict())

    def test_get_all_rsc_esx_clust(self):
        self._create_rscs()

        rsc_list = self.db_api.get_all_resources(
            self.context, session=self.session,
            **{'resource_mgr_id': fake_data.vc_data_uuid.get('id')})

        self.assertEqual(len(rsc_list), 1)

        rsc_list = self.db_api.get_all_resources(
            self.context, session=self.session,
            **{'type': 'esx_cluster'})

        self.assertEqual(len(rsc_list), 1)

    def test_get_all_rsc_rhel(self):
        self._create_rscs()

        rsc_list = self.db_api.get_all_resources(
            self.context, session=self.session, **{'type': 'rhel'})

        self.assertEqual(len(rsc_list), 2)

    def test_get_rsc_esx_clust(self):
        self.db_api.create_resource_manager(self.context, fake_data.vc_data,
                                            session=self.session)
        rsc = self.db_api.create_resource(
            self.context, fake_data.esxclust_data,
            session=self.session).to_dict()
        rsc_get = self.db_api.get_resource(
            self.context, rsc.get('id'), session=self.session).to_dict()
        self._assert_rsc_esx_cluster(rsc, rsc_get)
        self._assert_rsc_esx_cluster(fake_data.esxclust_data, rsc_get)

    def test_get_rsc_kvm(self):
        rsc = self.db_api.create_resource(
            self.context, fake_data.rhel_data, session=self.session).to_dict()
        rsc_get = self.db_api.get_resource(
            self.context, rsc.get('id'), session=self.session).to_dict()
        self._assert_rsc_kvm(rsc, rsc_get)
        self._assert_rsc_kvm(fake_data.rhel_data, rsc_get)

    def test_delete_rsc_esx_clust(self):
        self.db_api.create_resource_manager(self.context, fake_data.vc_data,
                                            session=self.session)
        rsc = self.db_api.create_resource(
            self.context, fake_data.esxclust_data,
            session=self.session).to_dict()
        rsc_del = self.db_api.delete_resource(
            self.context, rsc.get('id'), session=self.session).to_dict()
        self.assertRaises(exception.NotFound,
                          self.db_api.get_resource,
                          self.context, rsc_del.get('id'),
                          session=self.session)

    def test_delete_rsc_kvm(self):
        rsc = self.db_api.create_resource(
            self.context, fake_data.rhel_data1, session=self.session).to_dict()
        rsc_del = self.db_api.delete_resource(
            self.context, rsc.get('id'), session=self.session).to_dict()
        self.assertRaises(exception.NotFound,
                          self.db_api.get_resource,
                          self.context, rsc_del.get('id'),
                          session=self.session)

    def test_create_property(self):
        rsc = self.db_api.create_resource(
            self.context, fake_data.rhel_data, session=self.session).to_dict()
        parent_id = rsc.get('id')
        prop = self.db_api.create_property(
            self.context, parent_id, fake_data.rhel_prop_key,
            fake_data.rhel_prop_val,
            session=self.session).to_dict()
        self._assert_property(fake_data.rhel_prop_key, fake_data.rhel_prop_val,
                              parent_id, prop)
        self._assert_is_not_deleted(prop)

    def test_update_property(self):
        rsc = self.db_api.create_resource(
            self.context, fake_data.rhel_data, session=self.session).to_dict()
        parent_id = rsc.get('id')
        prop = self.db_api.create_property(
            self.context, parent_id, fake_data.rhel_prop_key,
            fake_data.rhel_prop_val,
            session=self.session).to_dict()
        prop_update = self.db_api.update_property(
            self.context, prop.get('id'), parent_id, fake_data.rhel_prop_key,
            fake_data.rhel_prop_val_update, session=self.session)

        self._assert_property(fake_data.rhel_prop_key,
                              fake_data.rhel_prop_val_update,
                              parent_id, prop_update)
        self._assert_is_not_deleted(prop_update)

    def _create_properties(self):
        key = [fake_data.rhel_prop_key, fake_data.rhel_prop_key1]
        val = [fake_data.rhel_prop_val, fake_data.rhel_prop_val1]

        rsc = self.db_api.create_resource(
            self.context, fake_data.rhel_data, session=self.session).to_dict()

        parent_id = rsc.get('id')
        self.db_api.create_property(self.context, parent_id, key[0], val[0],
                                    session=self.session)
        self.db_api.create_property(self.context, parent_id, key[1], val[1],
                                    session=self.session)
        return parent_id, key, val

    def test_get_properties(self):
        parent_id, key, val = self._create_properties()
        prop_list = self.db_api.get_properties(self.context, parent_id,
                                               session=self.session)

        self.assertEqual(len(prop_list), 2)
        for prop, k, v in zip(prop_list, key, val):
            self._assert_property(k, v, parent_id, prop.to_dict())
            self._assert_is_not_deleted(prop.to_dict())

    def test_get_property(self):
        parent_id, key, val = self._create_properties()
        prop = self.db_api.get_properties(
            self.context, parent_id, key=key[0],
            session=self.session)[0].to_dict()

        self._assert_property(key[0], val[0], parent_id, prop)
        self._assert_is_not_deleted(prop)

    def _assert_delete_for_properties(self, prop_del_list):
        for prop in prop_del_list:
            self.assertRaises(exception.NotFound,
                              self.db_api.get_properties,
                              self.context, prop.parent_id, prop.key,
                              self.session)

    def test_delete_properties(self):
        parent_id, key, val = self._create_properties()
        prop_del_list = self.db_api.delete_property(self.context, parent_id,
                                                    session=self.session)

        self.assertEqual(len(prop_del_list), 2)
        self._assert_delete_for_properties(prop_del_list)

    def test_delete_property(self):
        parent_id, key, val = self._create_properties()
        prop_del = self.db_api.delete_property(
            self.context, parent_id, key=key[0],
            session=self.session)[0]
        self._assert_delete_for_properties([prop_del])

    def test_create_resource_mgr_property(self):
        rsc_mgr = self.db_api.create_resource_manager(
            self.context, fake_data.vc_data, session=self.session).to_dict()
        parent_id = rsc_mgr.get('id')
        prop = self.db_api.create_resource_mgr_property(
            self.context, parent_id, fake_data.vc_prop_key,
            fake_data.vc_prop_val,
            session=self.session).to_dict()
        self._assert_property(fake_data.rhel_prop_key, fake_data.vc_prop_val,
                              parent_id, prop)
        self._assert_is_not_deleted(prop)

    def test_update_resource_mgr_property(self):
        rsc_mgr = self.db_api.create_resource_manager(
            self.context, fake_data.vc_data, session=self.session).to_dict()
        parent_id = rsc_mgr.get('id')
        prop = self.db_api.create_resource_mgr_property(
            self.context, parent_id, fake_data.vc_prop_key,
            fake_data.vc_prop_val,
            session=self.session).to_dict()
        prop_update = self.db_api.update_resource_mgr_property(
            self.context, prop.get('id'), parent_id, fake_data.vc_prop_key,
            fake_data.vc_prop_val_update, session=self.session)

        self._assert_property(fake_data.vc_prop_key,
                              fake_data.vc_prop_val_update,
                              parent_id, prop_update)
        self._assert_is_not_deleted(prop_update)

    def _create_resource_mgr_properties(self):
        key = [fake_data.vc_prop_key, fake_data.vc_prop_key1]
        val = [fake_data.vc_prop_val, fake_data.vc_prop_val1]

        rsc_mgr = self.db_api.create_resource_manager(
            self.context, fake_data.vc_data, session=self.session).to_dict()

        parent_id = rsc_mgr.get('id')
        self.db_api.create_resource_mgr_property(self.context, parent_id,
                                                 key[0], val[0],
                                                 session=self.session)
        self.db_api.create_resource_mgr_property(self.context, parent_id,
                                                 key[1], val[1],
                                                 session=self.session)
        return parent_id, key, val

    def test_get_resource_mgr_properties(self):
        parent_id, key, val = self._create_resource_mgr_properties()
        prop_list = self.db_api.get_resource_mgr_properties(
            self.context, parent_id, session=self.session)

        self.assertEqual(len(prop_list), 2)
        for prop, k, v in zip(prop_list, key, val):
            self._assert_property(k, v, parent_id, prop.to_dict())
            self._assert_is_not_deleted(prop.to_dict())

    def test_get_resource_mgr_property(self):
        parent_id, key, val = self._create_resource_mgr_properties()
        prop = self.db_api.get_resource_mgr_properties(
            self.context, parent_id, key=key[0],
            session=self.session)[0].to_dict()

        self._assert_property(key[0], val[0], parent_id, prop)
        self._assert_is_not_deleted(prop)

    def _assert_delete_for_resource_mgr_properties(self, prop_del_list):
        for prop in prop_del_list:
            self.assertRaises(exception.NotFound,
                              self.db_api.get_resource_mgr_properties,
                              self.context, prop.parent_id, prop.key,
                              self.session)

    def test_delete_resource_mgr_properties(self):
        parent_id, key, val = self._create_resource_mgr_properties()
        prop_del_list = self.db_api.delete_resource_mgr_property(
            self.context, parent_id, session=self.session)

        self.assertEqual(len(prop_del_list), 2)
        self._assert_delete_for_properties(prop_del_list)

    def test_delete_resource_mgr_property(self):
        parent_id, key, val = self._create_resource_mgr_properties()
        prop_del = self.db_api.delete_resource_mgr_property(
            self.context, parent_id, key=key[0],
            session=self.session)[0]
        self._assert_delete_for_properties([prop_del])

    def test_get_resource_mgrs_by_res_id(self):
        self.db_api.create_resource_manager(self.context, fake_data.vc_data,
                                            session=self.session)
        rsc = self.db_api.create_resource(
            self.context, fake_data.esxclust_data,
            session=self.session).to_dict()
        self.assertRaises(sqlalchemy.orm.exc.NoResultFound,
                          self.db_api.get_resource_managers_by_resource_id,
                          self.context, rsc["id"], self.session)
