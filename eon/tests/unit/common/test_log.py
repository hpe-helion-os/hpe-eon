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

import os
import fnmatch
from oslo_config import cfg

from eon.common.log import EonLogHandler
import eon.tests.unit.tests as unit_tests

CONF = cfg.CONF


class TestEonLogHandler(unit_tests.BaseTestCase):
    def setUp(self):
        super(TestEonLogHandler, self).setUp()
        self.log_name = "IscEsxActivateLogHandlerTest.log"

    def tearDown(self):
        for f in os.listdir('.'):
            if fnmatch.fnmatch(f, self.log_name + '*'):
                os.remove(f)
        super(TestEonLogHandler, self).tearDown()

    def test_log_IscEsxActivate_log_handler(self):
        handler = EonLogHandler(self.log_name, backupCount=3)
        with open(self.log_name + ".1.gz", "w"):
            pass
        handler.doRollover()
        self.assert_(os.path.exists(self.log_name), "Log file not found")
        self.assert_(os.path.exists(
            self.log_name + ".1.gz"), "Back file *.1.gz not found")
        self.assert_(os.path.exists(
            self.log_name + ".2.gz"), "Back file *.2.gz not found")

    def test_log_IscEsxActivate_log_handler_backup_full(self):
        handler = EonLogHandler(self.log_name, backupCount=3)
        with open(self.log_name + ".1.gz", "w"):
            pass
        with open(self.log_name + ".2.gz", "w"):
            pass
        with open(self.log_name + ".3.gz", "w"):
            pass
        handler.doRollover()
        self.assert_(os.path.exists(self.log_name), "Log file not found")
        self.assert_(os.path.exists(
            self.log_name + ".1.gz"), "Back file *.1.gz not found")
        self.assert_(os.path.exists(
            self.log_name + ".2.gz"), "Back file *.2.gz not found")
        self.assert_(os.path.exists(
            self.log_name + ".3.gz"), "Back file *.3.gz not found")
        self.assertFalse(os.path.exists(
            self.log_name + ".4.gz"), "Back file *.4.gz is found")

    def test_log_IscEsxActivate_log_handler_backup_nil(self):
        handler = EonLogHandler(self.log_name, backupCount=3)
        handler.doRollover()
        self.assert_(os.path.exists(self.log_name), "Log file not found")
        self.assert_(os.path.exists(
            self.log_name + ".1.gz"), "Back file *.1.gz not found")
