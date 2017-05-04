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
import logging
import os
import socket
import six
import time
from time import strftime
import paramiko
import re
from paramiko.ssh_exception import AuthenticationException,\
    BadHostKeyException, NoValidConnectionsError
from eon.common.exception import RhelCommandNoneZeroException,\
    AuthenticationError

from oslo_config import cfg
LOG = logging.getLogger(__name__)

CONF = cfg.CONF
opts = [cfg.IntOpt('ssh_connection_timeout', default=120,
                   help=(_('Timeout for the ssh connection in conductor')))]
CONF.register_opts(opts)

SUPER_USER = 'root'
_SANITIZE_OPTIONS = ['--password', 'admin_password', 'rabbitmq_password',
                     'activate_monasca mon-agent']
_SANITIZE_PATTERNS = []
_FORMAT_PATTERNS = [
    r'''(%(option)s\s+)['"].+?['"](\s+)''',
    r'''(%(option)s\s*)[^'"].+?(\s+)''',
    r'''(["']%(option)s["']\s+)['"].+?['"](\s+)''',
    r'''(["']%(option)s["']\s+)[^'"].+?(\s+)''',
]


for option in _SANITIZE_OPTIONS:
    for pattern in _FORMAT_PATTERNS:
        reg_ex = re.compile(pattern % {'option': option}, re.DOTALL)
        _SANITIZE_PATTERNS.append(reg_ex)


def _mask_sensitive_info(message, secret="***"):
    """Replace sensitive information with 'secret' in message.

    :param message: The string which includes sensitive information.
    :param secret: value with which to replace sensitive information.
    :returns: The unicode value of message with the password fields masked.

    For example:

    >>> mask_sensitive_info("useradd --password 'e1LpE3a8wKywY' 'hp-isc'")
    "useradd --password *** 'hp-isc'"
    >>> mask_sensitive_info("useradd --password 'e1LpE3  a8wKywY' 'hp-isc'")
    "useradd --password *** 'hp-isc'"
    >>> mask_sensitive_info("useradd --password e1LpE3a8wKywY 'hp-isc'")
    "useradd --password *** 'hp-isc'"
    >>> mask_sensitive_info("useradd '--password' 'e1LpE3a8wKywY' 'hp-isc'")
    "useradd '--password' *** 'hp-isc'"
    >>> mask_sensitive_info("useradd '--password' 'e1LpE3  a8wKywY' 'hp-isc'")
    "useradd '--password' *** 'hp-isc'"
    >>> mask_sensitive_info("useradd '--password' e1LpE3a8wKywY 'hp-isc'")
    "useradd '--password' *** 'hp-isc'"
    """
    message = six.text_type(message)

    if not any(option in message for option in _SANITIZE_OPTIONS):
        return message

    secret = r'\g<1>' + secret + r'\g<2>'
    for pattern in _SANITIZE_PATTERNS:
        message = re.sub(pattern, secret, message)
    return message


class RemoteConnection(object):

    '''Class to configure managed KVM hosts from the ISC appliance'''

    def __init__(self, host_or_ip, user, passwd=None, priv_key_file=None,
                 ssh_client=None, timeout=CONF.ssh_connection_timeout,
                 sleep_interval = 40):
        '''Initialize the configurator for the given hostname/IP with "
        "one-time configuration sudo (or root) credentials'''
        self._host_or_ip = host_or_ip
        self._user = user
        self._passwd = passwd
        self.timeout = timeout
        self.sleep_interval = sleep_interval
        if priv_key_file:
            self._priv_key_file = priv_key_file
        else:
            self._priv_key_file = None
        self._connected = False
        if ssh_client is not None:
            self._ssh_client = ssh_client
            self._connected = True
        self.remote_log = '/var/log/cloudsystem/activate.log'
        self._socket = None

    def open_connection(self, retry_on_novalidconnection_error=True):
        ''' Opens the SSH connection to the managed KVM host '''
        if not self._connected:
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy())
            if retry_on_novalidconnection_error:
                no_of_iterations = self.timeout / self.sleep_interval
            else:
                no_of_iterations = 1
            exception_to_raise_on_failure = None
            for i in range(0, no_of_iterations):
                try:
                    key = None
                    if self._priv_key_file is not None:
                        key = paramiko.RSAKey.from_private_key_file(
                            self._priv_key_file)

                    self._ssh_client.connect(self._host_or_ip,
                                             username=self._user,
                                             password=self._passwd, pkey=key,
                                             timeout=self.timeout)
                    self._connected = True
                    break
                except AuthenticationException, ae:
                    msg = (_('Unable to log in to host (%s).'
                             ' Invalid user name '
                             '(%s) or password: %s')) % (self._host_or_ip,
                                                         self._user, ae)
                    LOG.exception(ae)
                    raise AuthenticationError(err=msg)
                except BadHostKeyException, ke:
                    raise ke
                except NoValidConnectionsError as ae:
                    exception_to_raise_on_failure = ae
                    msg = ('Unable to log into host (%s): %s') % (
                        self._host_or_ip, str(ae))
                    LOG.warning(msg + " Will re-try connecting to %s."
                                " Attempt no - %s" % (str(self._host_or_ip),
                                                      str(i)))
                    if retry_on_novalidconnection_error:
                        time.sleep(self.sleep_interval)
                    continue
                except Exception, e:
                    msg = (_('Unable to contact the host (%s). '
                             'Ensure the host '
                             'is communicating on the CONF '
                             'Network: %s')) % (self._host_or_ip, e)
                    LOG.error(msg)
                    LOG.exception(e)
                    raise e

            if not self._connected:
                LOG.error("All %s attempts to reconnect"
                          " the host %s failed" % (str(no_of_iterations),
                                                   str(self._host_or_ip)))
                raise exception_to_raise_on_failure

    def close_connection(self):
        '''Close the SSH connection to the managed KVM host'''
        if self._ssh_client is not None:
            self._ssh_client.close()
        self._connected = False

    # TODO: these should probably be @properties instead of accessor methods
    def is_connected(self):
        return self._connected

    def is_online(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        try:
            sock.connect((self._host_or_ip, 22))
        except socket.error:
            return False
        else:
            return True
        finally:
            sock.close()

    def get_cmd_prefix(self):
        '''Returns a prefix for the command line to run the command
        as root if the user is not root.
        '''
        prefix = ''
        if self._user != SUPER_USER:
            prefix = '/usr/bin/sudo '
        return prefix

    def escape_sh(self, cmdlist):
        if not cmdlist:
            return ""
        for i in range(0, len(cmdlist)):
            cmdlist[i] = '"' + cmdlist[i].replace('"', '"""') + '"'
        return " ".join(cmdlist)

    def log_remote(self, line):
        '''Log the command to a file on the remote system.'''
        timestamp = strftime('%Y-%m-%d %H:%M:%S')
        try:
            line = _mask_sensitive_info(line)
            LOG.info('%s: "%s"', timestamp, line)
            sanitized_line = self.escape_sh(line.split())
            remote_log_cmd = (
                """/bin/echo %21s : %s >> %s""" % (
                    timestamp, sanitized_line, self.remote_log))
            prefixed_remote_log_cmd = self.prefix_command(remote_log_cmd)
            self._ssh_client.exec_command(prefixed_remote_log_cmd)
        except Exception as e:
            LOG.error(e)

    def exec_command(self, cmd):
        self.open_connection()
        self._ssh_client.exec_command(cmd)

    def exec_command_and_wait(self, cmd, raise_on_exit_not_0=False,
                              input_lines=None, hide_cmd=False):
        '''Execute the given command on the remote system,
        wait for it to return, then return the exit code'''
        channel = None
        try:
            self.open_connection()
            prefixed_cmd = self.prefix_command(cmd)
            if not hide_cmd:
                self.log_remote(prefixed_cmd)
            sanitized_cmd = self.escape_sh(prefixed_cmd.split())
            stdin, stdout, stderr = self._ssh_client.exec_command(
                sanitized_cmd)
            channel = stdout.channel
            channel.settimeout(600)
            exit_code = 0
            stdout_data = None
            stderr_data = None
            try:
                if input_lines is not None:
                    #
                    # If the output of the command exceeds about 100K bytes
                    # while sending input, the stdin.write() will hang because
                    # we do not read output while sending input.
                    #
                    for line in input_lines:
                        stdin.write(line + '\n')
                    stdin.flush()
                    stdin.channel.shutdown_write()
                stdout_data = stdout.read()
                exit_code = channel.recv_exit_status()
                stderr_data = stderr.read()
                stdin.close()
            except socket.timeout:
                self._connected = False
                raise
            finally:
                LOG.info("Exit code: %d  Stdout: %s  Stderr: %s" % (
                    exit_code, stdout_data, stderr_data))
            if exit_code != 0:
                if not hide_cmd:
                    self.log_remote('Exit code=%d  Command=%s STDOUT: %s '
                                    'STDERR: %s' %
                                (exit_code, cmd, stdout_data, stderr_data))
                else:
                    self.log_remote('Exit code=%d  STDOUT: %s '
                                    'STDERR: %s' %
                                (exit_code, stdout_data, stderr_data))
                if raise_on_exit_not_0:
                    raise RhelCommandNoneZeroException(
                        'exitcode = %d STDOUT: %s STDERR: %s' %
                        (exit_code, stdout_data, stderr_data))
            return (exit_code, stdout_data, stderr_data)
        except Exception:
            raise
        finally:
            if channel:
                channel.close()

    def prefix_command(self, command):
        """Insert the command prefix into the
        command at the required points."""
        prefix = self.get_cmd_prefix()
        appended_cmds = [cmd for cmd in command.split(";")
                         if cmd.strip() != ""]
        prefixed_cmds = []
        commands_to_skip_sudo = ['if', 'then', 'fi', 'do', 'done', 'for']

        def check_if_sudo_required(stripped_cmd):
            for non_sudo_cmd in commands_to_skip_sudo:
                if non_sudo_cmd in stripped_cmd:
                    return False
            return True

        def get_list_of_prefixed_cmds(piped_cmd):
            new_list = []
            for cmd in piped_cmd.split("|"):
                cmd = cmd.strip()
                if check_if_sudo_required(cmd):
                    new_list.append(prefix + cmd)
                else:
                    new_list.append(cmd)
            return new_list

        for piped_cmd in appended_cmds:
            prefixed_cmds.append(" | ".join(get_list_of_prefixed_cmds(
                piped_cmd)))

        return ' ; '.join(prefixed_cmds)

    def get(self, remote_path):
        '''Receive the remote file over SFTP'''
        tmp_path = "/tmp/" + os.path.basename(remote_path)
        try:
            os.remove(tmp_path)
        except:
            pass
        if not self._connected:
            self.open_connection()
        sftp = self._ssh_client.open_sftp()
        sftp.get(remote_path, tmp_path)
        sftp.close()
        return tmp_path

    def get_ssh_client(self):
        return self._ssh_client

    def does_file_exist(self, path):
        """
        Checks if the file exists
        :param path: full path of the file on the remote host
        :return: True/False
        """
        """
        :param path:
        :return:
        """
        try:
            self.open_connection()
            sftp = self._ssh_client.open_sftp()
            sftp.stat(path)
        except IOError as ie:
            if ie.errno == errno.ENOENT:
                return False
            raise
        else:
            return True
