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


import winrm
import base64
from oslo_config import cfg

import eon.common.log as logging
from eon.common import exception
from winrm.protocol import Protocol


LOG = logging.getLogger(__name__)

_Auth_Failed_Msg = "basic auth failed"

opts = [cfg.IntOpt("pywinrm_timeout", default=300,
                   help="Pywinrm connection to hyperv timeout.")
        ]
CONF = cfg.CONF
CONF.register_opts(opts)


def _handle_winrm_exception(fn):
    """ Handle winrm.exceptions.WinRMTransportError and raises properly.

    :raises
    exception.PyWinRMAuthenticationError
    exception.PyWinRMConnectivityError
    """
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except winrm.exceptions.WinRMTransportError as exc:
            LOG.info("Pywinrm exception: %s" % exc)

            if _Auth_Failed_Msg in exc.message:
                raise exception.PyWinRMAuthenticationError()

            raise exception.PyWinRMConnectivityError(err=exc.message)

    return wrapper


def get_pywinrm_session(ip, port, username, password):
    '''Get an insecure pywinrm session.

    :params ip, username, password: Windows host's WinRM details.
    :param port: the port where the WinRM service is listening in host.
    '''
    transport_protocols = {
        'http': ('plaintext', 'http'),
        'https': ('ssl', 'https')
        }
    transport, protocol = transport_protocols['http' if port == 5985
                                              else 'https']
    session = winrm.Session("%(protocol)s://%(ip)s:%(port)s/wsman" % {
        "ip": ip, "port": port, "protocol": protocol},
        auth=(username, password), transport=transport)
    session.protocol = Protocol(session.url, transport=transport,
                                username=username, password=password,
                                server_cert_validation='ignore')
    return session


@_handle_winrm_exception
def run_cmd_low_level(session, cmd_script, timeout=CONF.pywinrm_timeout):
    '''Execute a cmd script with timeout(wait for output), low level.

    :param session: Returned by get_pywinrm_session().
    :param cmd_script: A script that need to be run by cmd.exe.
    :param timeout: time to wait for the @cmd_script to finish in secs.
    '''
    protocol = session.protocol
    protocol.DEFAULT_TIMEOUT = "PT%dS" % timeout

    cmd_list = cmd_script.split()

    shell_id = protocol.open_shell()
    command_id = protocol.run_command(shell_id, cmd_list[0], cmd_list[1:])
    std_out, std_err, status_code = protocol.get_command_output(shell_id,
                                                                command_id)

    protocol.cleanup_command(shell_id, command_id)
    protocol.close_shell(shell_id)
    return (std_out, std_err, status_code)


@_handle_winrm_exception
def run_cmd_script(session, cmd_script, timeout=CONF.pywinrm_timeout):
    '''Execute a cmd script with timeout(wait for output).

    :param session: Returned by get_pywinrm_session()
    :param cmd_script: script that need to be run by cmd.exe
    :param timeout: time to wait for the @cmd_script to finish in secs.
    '''
    protocol = session.protocol
    protocol.timeout = "PT%dS" % timeout

    cmd_list = cmd_script.split()
    resp = session.run_cmd(cmd_list[0], cmd_list[1:])
    return resp


@_handle_winrm_exception
def run_ps_script(session, ps_script, timeout=CONF.pywinrm_timeout):
    '''Execute a Powershell script with timeout(wait for output).

    :param session: Returned by get_pywinrm_session().
    :param ps_script: script that need to be run by powershell.exe.
    :param timeout: time to wait for the @ps_script to finish in secs.
    '''
    protocol = session.protocol
    protocol.timeout = "PT%dS" % timeout

    ps_script = "\n%s" % ps_script
    ps_script_enc = base64.b64encode(ps_script.encode("utf-16"))

    cmd = ("powershell -executionpolicy Bypass -encodedcommand %s"
           % ps_script_enc)
    cmd_list = cmd.split()
    resp = session.run_cmd(cmd_list[0], cmd_list[1:])

    return resp


@_handle_winrm_exception
def run_ps_script_copy_file(session, ps_script, timeout=CONF.pywinrm_timeout):
    '''Execute a Powershell script with timeout(wait for output).

    :param session: Returned by get_pywinrm_session().
    :param ps_script: script that need to be run by powershell.exe.
    :param timeout: time to wait for the @ps_script to finish in secs.
    '''
    protocol = session.protocol
    protocol.timeout = "PT%dS" % timeout

    ps_script = "\n%s" % ps_script
    ps_script_enc = base64.b64encode(ps_script.encode("utf-16"))

    cmd = ("powershell -encodedcommand %s"
           % ps_script_enc)
    resp = session.run_cmd(cmd)

    return resp
