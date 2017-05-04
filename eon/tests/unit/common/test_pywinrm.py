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

from testtools import TestCase
from mock import MagicMock
from mock import patch
import winrm

from eon.virt.hyperv import pywinrm
from eon.common import exception


class TestPywinrm(TestCase):
    @classmethod
    def setUpClass(cls):
        TestCase.setUpClass()

        cls.ip = "10.1.8.8"
        cls.port = "5985"
        cls.username = "Administrator"
        cls.password = "password"

        cls.ps_script = "ls"
        cls.cmd_script = "dir"

        cls.cmd_output_tuple = ("std_out", "std_err", 0)
        cls.connection_err = \
            "Connection fail OR WinRM not properly configured..."

    @classmethod
    def tearDownClass(cls):
        TestCase.tearDownClass()

    def setUp(self):
        TestCase.setUp(self)

    def tearDown(self):
        TestCase.tearDown(self)

    def test_get_pywinrm_session(self):
        with patch.object(pywinrm, "winrm"):
            pywinrm.winrm = MagicMock()
            ses = pywinrm.winrm.Session.return_value = MagicMock()

            ses_ret = pywinrm.get_pywinrm_session(
                self.ip, self.port, self.username, self.password)

            self.assertEqual(ses, ses_ret)

    def test_run_cmd_script(self):
        ses = MagicMock()
        resp = ses.run_cmd.return_value = MagicMock()

        resp_ret = pywinrm.run_cmd_script(ses, self.cmd_script)

        self.assertEqual(resp, resp_ret)

    def test_run_cmd_script_invalid_credentials(self):
        ses = MagicMock()
        transport = MagicMock()
        ses.run_cmd = MagicMock(
            side_effect=winrm.exceptions.WinRMTransportError(
                transport, pywinrm._Auth_Failed_Msg))

        self.assertRaises(exception.PyWinRMAuthenticationError,
                          pywinrm.run_cmd_script,
                          ses,
                          self.cmd_script)

    def test_run_cmd_script_connection_error(self):
        ses = MagicMock()
        transport = MagicMock()
        ses.run_cmd = MagicMock(
            side_effect=winrm.exceptions.WinRMTransportError(
                transport, self.connection_err))

        self.assertRaises(exception.PyWinRMConnectivityError,
                          pywinrm.run_cmd_script,
                          ses,
                          self.cmd_script)

    def test_run_ps_script(self):
        ses = MagicMock()
        resp = ses.run_cmd.return_value = MagicMock()

        resp_ret = pywinrm.run_ps_script(ses, self.ps_script)

        self.assertEqual(resp, resp_ret)

    def test_run_cmd_low_level(self):
        ses = MagicMock()
        resp = ses.protocol.get_command_output.return_value = \
            self.cmd_output_tuple

        resp_ret = pywinrm.run_cmd_low_level(
            ses, self.cmd_script, timeout=60)

        self.assertEqual(resp, resp_ret)

    def test_run_ps_script_copy_file(self):
        ses = MagicMock()
        resp = ses.run_cmd.return_value = MagicMock()

        resp_ret = pywinrm.run_ps_script_copy_file(ses, self.ps_script)

        self.assertEqual(resp, resp_ret)
