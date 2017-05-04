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

import errno
import socket
from testtools import TestCase
from mock import Mock
from mock import call
from mock import patch
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import BadHostKeyException
from paramiko.ssh_exception import NoValidConnectionsError
from paramiko.sftp_file import SFTPFile
from paramiko import pkey

from eon.tests.unit import base_test
from eon.virt import constants as kvm_constants

from eon.common import exception
from eon.common import ssh_utilities


class TestSSHConnection(base_test.TestCase):

    def setUp(self):
        super(TestSSHConnection, self).setUp()
        self.hostname = "test"
        self.user = "test"
        self.passwd = "test"
        self.priv_key_file = "test"
        self.ssh_client = Mock()
        self.sftp_client = Mock()
        self.ssh_stdout_mock = Mock()
        self.ssh_stdin_mock = Mock()
        self.ssh_stdin_mock.channel = Mock()
        self.channel_mock = Mock()
        self.paramiko_mock = Mock()

        self.channel_mock.recv_exit_status.return_value = 0
        self.ssh_stdout_mock.channel = self.channel_mock
        self.ssh_client.open_sftp.return_value = self.sftp_client
        self.ssh_client.exec_command.return_value = \
            [self.ssh_stdin_mock, self.ssh_stdout_mock, Mock()]

    @classmethod
    def tearDownClass(cls):
        TestCase.tearDownClass()

    def tearDown(self):
        TestCase.tearDown(self)

    def test_get_ssh_client(self):
        with patch('paramiko.SSHClient'):
            configurator = \
                ssh_utilities.RemoteConnection(self.hostname, self.user,
                                            self.passwd,
                                            ssh_client=self.ssh_client)
            configurator.open_connection()
            self.assertNotEqual(None, configurator.get_ssh_client())

    @patch('paramiko.RSAKey.from_private_key_file')
    @patch('paramiko.SSHClient')
    def test_open_connection_with_priv_key(self, sshClient, rsaKey):
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   priv_key_file="file")
        configurator.open_connection()
        self.assertTrue(configurator.is_connected())

    @patch('paramiko.SSHClient.connect')
    def test_open_connection_without_retrials(self, mocked_connect):
        configurator = ssh_utilities.RemoteConnection(self.hostname,
                                                      self.user,
                                                      self.passwd)
        configurator.open_connection()
        self.assertTrue(configurator.is_connected())
        mocked_connect.assert_called_once_with(self.hostname,
                                               username=self.user,
                                               password=self.passwd,
                                               pkey=None,
                                               timeout=configurator.timeout)
        self.assertEquals(1, mocked_connect.call_count)

    @patch('paramiko.SSHClient.connect')
    def test_open_connection_connect_exception(self, mocked_connect):
        error = {"somekey": "someval"}
        exc = NoValidConnectionsError(error)
        mocked_connect.side_effect = [exc, exc, exc]
        configurator = ssh_utilities.RemoteConnection(self.hostname,
                                                      self.user,
                                                      self.passwd)
        configurator.timeout = 3
        configurator.sleep_interval = 1
        self.assertRaises(NoValidConnectionsError,
                          configurator.open_connection)
        self.assertEquals(configurator.is_connected(), False)
        self.assertEquals(3, mocked_connect.call_count)

    @patch('paramiko.SSHClient.connect')
    def test_open_connection_connect_exception2(self, mocked_connect):
        error = {"somekey": "someval"}
        exc = NoValidConnectionsError(error)
        mocked_connect.side_effect = [exc]
        configurator = ssh_utilities.RemoteConnection(
            self.hostname, self.user, self.passwd)
        configurator.timeout = 3
        configurator.sleep_interval = 1
        self.assertRaises(NoValidConnectionsError,
                          configurator.open_connection,
                          retry_on_novalidconnection_error=False)
        self.assertEquals(1, mocked_connect.call_count)

    @patch('paramiko.SSHClient')
    def test_open_connection_exception(self, sshClient):
        sshClient.return_value.connect = Mock(side_effect=Exception)
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd)
        self.assertRaises(Exception, configurator.open_connection)

    @patch('paramiko.SSHClient')
    @patch('paramiko.RSAKey.from_private_key_file')
    def test_open_connection_authentication_exception(self, mock_rsa,
                                                      sshClient):
        sshClient.return_value.connect = Mock(
            side_effect=AuthenticationException())
        configurator = ssh_utilities.RemoteConnection(
            self.hostname, user=self.user, passwd=self.passwd,
            priv_key_file=self.priv_key_file)
        self.assertRaises(exception.AuthenticationError,
                          configurator.open_connection)

    @patch('paramiko.SSHClient')
    @patch('paramiko.RSAKey.from_private_key_file')
    def test_open_connection_badhostkey_exception(self, mock_rsa, sshClient):
        got_key = pkey.PKey("sadad")
        expected_key = pkey.PKey("sadadaa")
        sshClient.return_value.connect = Mock(
            side_effect=BadHostKeyException(
                self.hostname, got_key, expected_key))
        configurator = ssh_utilities.RemoteConnection(
            self.hostname, user=self.user, passwd=self.passwd,
            priv_key_file=self.priv_key_file)
        self.assertRaises(BadHostKeyException, configurator.open_connection)

    @patch('paramiko.SSHClient')
    @patch('paramiko.RSAKey.from_private_key_file')
    def test_open_connection_authentication_exception_multiple_retries(
            self, mock_rsa, sshClient):
        sshClient.return_value.connect = Mock(
            side_effect=AuthenticationException())
        configurator = ssh_utilities.RemoteConnection(
            self.hostname, user=self.user, passwd=self.passwd,
            priv_key_file=self.priv_key_file)
        self.assertRaises(exception.AuthenticationError,
            configurator.open_connection)

    @patch('socket.socket')
    def test_is_online_true(self, socket_arg):
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd)
        self.assertTrue(configurator.is_online())

    @patch('socket.socket')
    def test_is_online_false(self, socket_arg):
        socket_arg.return_value.connect = Mock(side_effect=socket.error)
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd)
        self.assertFalse(configurator.is_online())

    def test_escape_sh(self):
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd)
        cmd = """uname -r | grep "^3.10" ; /bin/sh/ \"rm -rf *\";"""
        expected_sanit_cmd = '''"uname" "-r" "|" "grep" """"^3.10"""" ";"''' \
            ''' "/bin/sh/" """"rm" "-rf" "*""";"'''
        sanit_cmd = configurator.escape_sh(cmd.split())
        self.assertEquals(expected_sanit_cmd, sanit_cmd)

    def test_exec_command_nonzero_exit_code(self):
        yum_cmd = "yum clean all"
        configurator = ssh_utilities.RemoteConnection(self.hostname,
                                                   self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        stdout = Mock()
        stdout.channel.recv_exit_status = Mock(return_value=1)
        self.ssh_client.exec_command.return_value = (Mock(), stdout, Mock())
        configurator.exec_command(yum_cmd)
        arg = self.ssh_client.exec_command.call_args.get(0)
        self.assertTrue(arg.contains("STDOUT"))
        self.assertTrue(arg.contains("STDERR"))
        self.assertTrue(arg.contains("activate.log"))

    def test_exec_command(self):
        yum_cmd = "yum clean all"
        calls = [call("yum clean all")]
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        configurator.exec_command(yum_cmd)
        self.ssh_client.exec_command.assert_has_calls(calls)

    def test_exec_command_fakecmd(self):
        fake_cmd = "noexistcmd"
        calls = [call("noexistcmd")]
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        configurator.exec_command(fake_cmd)
        self.ssh_client.exec_command.assert_has_calls(calls)

    def test_exec_command_and_wait(self):
        yum_cmd = "yum clean all"
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        stdout = Mock()
        stdout.channel.recv_exit_status = Mock(return_value=1)
        stdout.read = Mock(return_value="validoutput")
        self.ssh_client.exec_command.return_value = (Mock(), stdout, Mock())
        exit_code, stdout_data, stderr_data = configurator.\
            exec_command_and_wait(yum_cmd)
        self.assertEquals(stdout_data, "validoutput")

    def test_exec_command_and_wait_input_lines(self):
        yum_cmd = "yum clean all"
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        stdout = Mock()
        stdout.channel.recv_exit_status = Mock(return_value=1)
        stdout.read = Mock(return_value="validoutput")
        self.ssh_client.exec_command.return_value = (Mock(), stdout, Mock())
        exit_code, stdout_data, stderr_data = configurator.\
            exec_command_and_wait(yum_cmd, input_lines="tee my.log")
        self.assertEquals(stdout_data, "validoutput")

    def test_exec_command_and_wait_input_lines_scoket_timeout(self):
        yum_cmd = "yum clean all"
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        stdout = Mock()
        stdout.channel.recv_exit_status = Mock(return_value=1)
        stdout.read = Mock(side_effect=socket.timeout)
        self.ssh_client.exec_command.return_value = (Mock(), stdout, Mock())
        self.assertRaises(socket.timeout, configurator.exec_command_and_wait,
                          yum_cmd, input_lines="tee my.log")

    def test_exec_command_and_wait_hide_cmd(self):
        yum_cmd = "yum clean all"
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        stdout = Mock()
        stdout.channel.recv_exit_status = Mock(return_value=1)
        stdout.read = Mock(return_value="validoutput")
        self.ssh_client.exec_command.return_value = (Mock(), stdout, Mock())
        exit_code, stdout_data, stderr_data = configurator.\
            exec_command_and_wait(yum_cmd,
                                  input_lines="tee my.log", hide_cmd=True)
        self.assertEquals(stdout_data, "validoutput")

    def test_exec_command_and_wait_raise_on_exit(self):
        yum_cmd = "yum clean all"
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        stdout = Mock()
        stdout.channel.recv_exit_status = Mock(return_value=1)
        stdout.read = Mock(return_value="error")
        self.ssh_client.exec_command.return_value = (Mock(), stdout, Mock())
        self.assertRaises(Exception, configurator.exec_command_and_wait,
                          yum_cmd, input_lines="tee my.log",
                          raise_on_exit_not_0=True)

    def test_get(self):
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        path = configurator.get(kvm_constants.SUBSCRIPTION_REPO_PATH)
        expected_path = '/tmp/subscription-manager.conf'
        self.assertEquals(path, expected_path)

    @patch('paramiko.SSHClient')
    def test_get_new_con(self, mocked_ssh):
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        configurator._connected = False
        path = configurator.get(kvm_constants.SUBSCRIPTION_REPO_PATH)
        expected_path = '/tmp/subscription-manager.conf'
        self.assertEquals(path, expected_path)

    def test_close_connection(self):
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        configurator.close_connection()
        self.assertTrue(not configurator._connected)

    def test_log_remote(self):
        self.ssh_client.exec_command.side_effect = [Exception]
        configurator = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd,
                                                   ssh_client=self.ssh_client)
        self.assertRaises(Exception, configurator.log_remote("log me"))

    def test_mask_sensitive_info_without_pass(self):
        expected_msg = "Hi There"
        actual_msg = ssh_utilities._mask_sensitive_info(expected_msg)
        self.assertEquals(expected_msg, actual_msg)

    def test_mask_sensitive_info(self):
        msg = "Hi There, --password secret "
        expected_msg = "Hi There, --password *** "
        actual_msg = ssh_utilities._mask_sensitive_info(msg)
        self.assertEquals(expected_msg, actual_msg)

    @patch("paramiko.sftp_file.SFTPFile.stat")
    @patch("paramiko.SSHClient.open_sftp")
    @patch("paramiko.SSHClient.connect")
    def test_does_file_exists_false(self, m_connect, m_opensftp, m_stat):
        ssh_util = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd)
        m_opensftp.return_value = SFTPFile("sftp", "handle")
        ioError = IOError()
        ioError.errno = errno.ENOENT
        m_stat.side_effect = [ioError]
        exists = ssh_util.does_file_exist("/etc/hos/osconfig-ran")
        self.assertEquals(exists, False)
        calls = [call(self.hostname, password=self.passwd,
                      pkey=None, timeout=120, username=self.user)]
        m_connect.assert_has_calls(calls)
        self.assertEquals(m_connect.call_count, 1)
        m_opensftp.assert_called_once_with()
        m_stat.assert_called_once_with("/etc/hos/osconfig-ran")

    @patch("paramiko.sftp_file.SFTPFile.stat")
    @patch("paramiko.SSHClient.open_sftp")
    @patch("paramiko.SSHClient.connect")
    def test_does_file_exists_true(self, m_connect, m_opensftp, m_stat):
        ssh_util = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd)
        m_opensftp.return_value = SFTPFile("sftp", "handle")
        exists = ssh_util.does_file_exist("/etc/hos/osconfig-ran")
        self.assertEquals(exists, True)
        calls = [call(self.hostname, password=self.passwd,
                      pkey=None, timeout=120, username=self.user)]
        m_connect.assert_has_calls(calls)
        self.assertEquals(m_connect.call_count, 1)
        m_opensftp.assert_called_once_with()
        m_stat.assert_called_once_with("/etc/hos/osconfig-ran")

    @patch("paramiko.sftp_file.SFTPFile.stat")
    @patch("paramiko.SSHClient.open_sftp")
    @patch("paramiko.SSHClient.connect")
    def test_does_file_exists_exception(self, m_connect, m_opensftp, m_stat):
        ssh_util = ssh_utilities.RemoteConnection(self.hostname, self.user,
                                                   self.passwd)
        m_opensftp.return_value = SFTPFile("sftp", "handle")
        m_stat.side_effect = [IOError]
        self.assertRaises(IOError, ssh_util.does_file_exist,
                          "/etc/hos/osconfig")
