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

import sys
from mock import patch
from testtools import TestCase
from oslo_config import cfg
from eon.cmd import oneview

CONF = cfg.CONF


class TestOneviewCmd(TestCase):

    @patch("eon.openstack.common.service.Launcher.wait")
    @patch("eon.common.service.RPCService")
    @patch("eon.common.service.prepare_service")
    def testMain(self, mocked_service, mocked_rpc, mocked_launch):
        oneview.main()
        mocked_service.assert_called_once_with(sys.argv)
        mocked_rpc.assert_called_once_with(CONF.host,
                                           'eon.oneview.manager',
                                           'OneviewManager')
        mocked_launch.assert_called_once_with()
