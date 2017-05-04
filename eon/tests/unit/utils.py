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

import unittest
import __builtin__
import datetime

import os
from oslo_config import cfg
import mox
import stubout
import eon

from eon.db.sqlalchemy import models


UUID1 = 'c80a1a6c-bd1f-41c5-90ee-81afedb1d58d'


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.mox = mox.Mox()
        self.stubs = stubout.StubOutForTesting()
        self._overridden_opts = []

    def tearDown(self):
        """Runs after each test method to tear down test environment."""
        self.mox.UnsetStubs()
        self.stubs.UnsetAll()
        self.stubs.SmartUnsetAll()
        self.mox.VerifyAll()
        super(BaseTestCase, self).tearDown()

    def config(self, **kw):
        ''' Override configuration values '''
        group = kw.pop('group', None)
        for k, v in kw.iteritems():
            CONF.set_override(k, v, group)

    def assertIn(self, a, b, *args, **kwargs):
        """Python < v2.7 compatibility.  Assert 'a' in 'b'"""
        try:
            f = super(TestCase, self).assertIn
        except AttributeError:
            self.assertTrue(a in b, *args, **kwargs)
        else:
            f(a, b, *args, **kwargs)

    def assertNotIn(self, a, b, *args, **kwargs):
        """Python < v2.7 compatibility.  Assert 'a' NOT in 'b'"""
        try:
            f = super(TestCase, self).assertNotIn
        except AttributeError:
            self.assertFalse(a in b, *args, **kwargs)
        else:
            f(a, b, *args, **kwargs)

    def checkEqual(self, l1, l2):
        return len(l1) == len(l2) and sorted(l1) == sorted(l2)


setattr(__builtin__, '_', lambda x: x)
CONF = cfg.CONF
CONF.import_opt('esx_sql_connection', 'eon.db')


class DbTestCase(BaseTestCase):

    def setUp(self):
        super(DbTestCase, self).setUp()
        ''' for eon create db '''
        eon_path = os.path.abspath(
            os.path.join(eon.get_eon_loc(), '../'))
        sql_connection_url = "sqlite:///" + str(eon_path) + "/tests.sqlite"
        CONF.set_default("esx_sql_connection", sql_connection_url)
        self.testdb = os.path.join(eon_path, "tests.sqlite")
        if os.path.exists(self.testdb):
            return
        else:
            open(self.testdb, 'w').close()

    def setup_sqlite(self, db_migrate):
        if db_migrate.version():
            return
        models.Base.metadata.create_all(self.db_api.get_engine())
        db_migrate.stamp('head')
        db_migrate.upgrade('head')

    def tearDown(self):
        """Runs after each test method to tear down test environment."""
        # TODO: add a flag which decides sqlite file needs to be clean.
        if os.path.exists(self.testdb):
            os.remove(self.testdb)
        super(DbTestCase, self).tearDown()

    def _assert_vcenter(self, vcenter1, vcenter2):
        self.assertEqual(vcenter1['name'], vcenter2['name'])
        self.assertEqual(vcenter1['ip_address'], vcenter2['ip_address'])
        self.assertEqual(vcenter1['username'], vcenter2['username'])
        self.assertEqual(vcenter1['password'], vcenter2['password'])
        self.assertEqual(vcenter1['port'], vcenter2['port'])

    def _assert_is_not_deleted(self, obj):
        self.assertNotEqual(obj['id'], None)
        self.assertEqual(obj['deleted_at'], None)

    def _assert_esx_proxy(self, esxproxy1, esxproxy2):
        self.assertEqual(esxproxy1['name'], esxproxy2['name'])
        self.assertEqual(esxproxy1['ip_address'], esxproxy2['ip_address'])
        self.assertEqual(esxproxy1['routing_key'], esxproxy2['routing_key'])
        self.assertEqual(esxproxy1['hostname'], esxproxy2['hostname'])

    def _assert_resource(self, resource1, resource2):
        self.assertEqual(resource1['name'], resource2['name'])
        self.assertEqual(resource1['vcenter_id'], resource2['vcenter_id'])
        self.assertEqual(resource1['path'], resource2['path'])
        self.assertEqual(resource1['type'], resource2['type'])
        self.assertEqual(resource1['esx_proxy_id'], resource2['esx_proxy_id'])

    def _assert_is_deleted(self, obj):
        self.assertEqual(bool(obj['deleted']), True)
        self.assertEqual(type(obj['deleted_at']), datetime.datetime)

    def _assert_vshield_props(self, props, vcenter):
        for prop in props:
            self.assertEqual(vcenter[prop['name']], prop['value'])

    def _assert_vcenter_property(self, prop1, prop2):
        self.assertEqual(prop1['name'], prop2['name'])
        self.assertEqual(prop1['type'], prop2['type'])
        self.assertEqual(prop1['value'], prop2['value'])
        self.assertEqual(prop1['resource_id'], prop2['resource_id'])
