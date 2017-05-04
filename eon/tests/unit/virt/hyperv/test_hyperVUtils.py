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

import mock

from eon.virt.hyperv import hyperv_utils
from eon.virt import constants
from eon.common import exception
from eon.tests.unit import base_test
from eon.tests.unit import fake_data


class Response(object):
    """Response from a remote command execution"""
    def __init__(self, args):
        self.std_out, self.std_err, self.status_code = args

    def __repr__(self):
        # TODO put tree dots at the end if out/err was truncated
        return '<Response code {0}, out "{1}", err "{2}">'.format(
            self.status_code, self.std_out[:20], self.std_err[:20])


class FakeContext(object):

    def __init__(self):
        self.auth_token = "509ba3bce14444079985c5ecf21760dc"


class TestHyperVUtils(base_test.TestCase):
    def setUp(self):
        super(TestHyperVUtils, self).setUp()

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_hostname(self, mocked_pywinrm, mocked_psscript):
        mocked_session_object = None
        mocked_pywinrm.return_value = mocked_session_object
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('WIN-4NAOV9N2DCH', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_psscript.return_value = resp
        hyperv_utilities.get_hostname()
        mocked_pywinrm.assert_called_once_with(
            resource_inventory[constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)
        mocked_psscript.assert_called_once_with(
            mocked_session_object, constants.PS_SCRIPT_TO_GET_HOSTNAME)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_hostname_exception(self, mocked_pywinrm, mocked_psscript):
        mocked_session_object = None
        mocked_pywinrm.return_value = mocked_session_object
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('WIN-4NAOV9N2DCH', '', 1,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_psscript.return_value = resp
        self.assertRaises(exception.HyperVPSScriptError,
                          hyperv_utilities.get_hostname)
        mocked_pywinrm.assert_called_once_with(
            resource_inventory[constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)
        mocked_psscript.assert_called_once_with(
            mocked_session_object, constants.PS_SCRIPT_TO_GET_HOSTNAME)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_get_csv_exception(self, mocked_pywinrm, mocked_psscript):
        mocked_session_object = None
        mocked_pywinrm.return_value = mocked_session_object
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('Host', '', 1,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_psscript.return_value = resp
        self.assertRaises(exception.HyperVPSScriptError,
                          hyperv_utilities.get_csv)
        mocked_pywinrm.assert_called_once_with(
            resource_inventory[constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)
        mocked_psscript.assert_called_once_with(
            mocked_session_object, constants.PS_SCRIPT_TO_CHECK_CSV)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_get_csv_not_cluster(self, mocked_pywinrm, mocked_psscript):
        mocked_session_object = None
        mocked_pywinrm.return_value = mocked_session_object
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('Standalone', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_psscript.return_value = resp
        hyperv_utilities.get_csv()
        mocked_pywinrm.assert_called_once_with(
            resource_inventory[constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)
        mocked_psscript.assert_called_once_with(
            mocked_session_object, constants.PS_SCRIPT_TO_CHECK_CSV)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_get_csv_valid_cluster(self, mocked_pywinrm, mocked_psscript):
        mocked_session_object = None
        mocked_pywinrm.return_value = mocked_session_object
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('Cluster', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_psscript.return_value = resp
        hyperv_utilities.get_csv()
        mocked_pywinrm.assert_called_once_with(
            resource_inventory[constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)
        mocked_psscript.assert_called_once_with(
            mocked_session_object, constants.PS_SCRIPT_TO_CHECK_CSV)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_get_csv_invalid_cluster(self, mocked_pywinrm, mocked_psscript):
        mocked_session_object = None
        mocked_pywinrm.return_value = mocked_session_object
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('C:\ClusterStorage\Volume1', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_psscript.return_value = resp
        hyperv_utilities.get_csv()
        mocked_pywinrm.assert_called_once_with(
            resource_inventory[constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)
        mocked_psscript.assert_called_once_with(
            mocked_session_object, constants.PS_SCRIPT_TO_CHECK_CSV)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_get_csv_not_enabled(self, mocked_pywinrm, mocked_psscript):
        mocked_session_object = None
        mocked_pywinrm.return_value = mocked_session_object
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_psscript.return_value = resp
        hyperv_utilities.get_csv()
        mocked_pywinrm.assert_called_once_with(
            resource_inventory[constants.EON_RESOURCE_IP_ADDRESS],
            resource_inventory[constants.EON_RESOURCE_PORT],
            resource_inventory[constants.EON_RESOURCE_USERNAME],
            resource_inventory[constants.EON_RESOURCE_PASSWORD],)
        mocked_psscript.assert_called_once_with(
            mocked_session_object, constants.PS_SCRIPT_TO_CHECK_CSV)

    def test_get_ps_script_to_copy_script(self):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        hyperv_utilities._get_ps_script_to_copy_script()

    def test_get_ps_script_to_remove_file(self):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        hyperv_utilities._get_ps_script_to_remove_file()

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'model_generated_host_name')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'get_server_by_role')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils._execute_script')
    def test_get_host_validation_data(self, mocked_execute, mocked_get_server,
                                      mocked_get_hostname, mocked_psscript):
        context = FakeContext()
        mocked_execute.return_value = {
            u'iSCSI_initiator_service_state': True,
            u'valid_compute_name': True,
            u'hostname': u'WIN-4NAOV9N2DCH',
            u'os_version': {u'Major': 6,
                            u'MajorRevision': 0,
                            u'MinorRevision': 0,
                            u'Build': 9600,
                            u'Minor': 3,
                            u'Revision': 0},
            u'ipaddresses': [u'10.1.214.32',
                             u'169.254.247.161',
                             u'169.254.205.230',
                             u'12.12.12.69',
                             u'192.168.28.63',
                             u'127.0.0.1'],
            u'os_edition': {u'number': 8,
                            u'name': u'Microsoft Windows Server 2012'
                                     u' R2 Datacenter'},
            u'vm_count': 0}
        resource_inventory = fake_data.hyperv_resource_inventory

        mocked_get_server.return_value = [
            {"id": "ccn1-0001",
             "role": "MANAGEMENT-ROLE"
             },
           ]
        mocked_get_hostname.return_value = 'cs-ccp-mgmt-m1-clm'
        args = ('true', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        mocked_psscript.return_value = resp
        returned_inventory = hyperv_utilities.get_host_validation_data(context)
        self.assertEquals(returned_inventory.get('host_date_configured'),
                          'true')
        mocked_execute.assert_called_once_with()
        mocked_get_server.assert_called_once_with('MANAGEMENT-ROLE')

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'model_generated_host_name')
    @mock.patch('eon.hlm_facade.hlm_facade_handler.HLMFacadeWrapper.'
                'get_server_by_role')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils._execute_script')
    def test_get_host_validation_data_ex(self, mocked_execute,
                                         mocked_get_server,
                                         mocked_get_hostname, mocked_psscript):
        context = FakeContext()
        mocked_execute.return_value = {
            u'iSCSI_initiator_service_state': True,
            u'valid_compute_name': True,
            u'hostname': u'WIN-4NAOV9N2DCH',
            u'os_version': {u'Major': 6,
                            u'MajorRevision': 0,
                            u'MinorRevision': 0,
                            u'Build': 9600,
                            u'Minor': 3,
                            u'Revision': 0},
            u'ipaddresses': [u'10.1.214.32',
                             u'169.254.247.161',
                             u'169.254.205.230',
                             u'12.12.12.69',
                             u'192.168.28.63',
                             u'127.0.0.1'],
            u'os_edition': {u'number': 8,
                            u'name': u'Microsoft Windows Server 2012'
                                     u' R2 Datacenter'},
            u'vm_count': 0}
        resource_inventory = fake_data.hyperv_resource_inventory

        mocked_get_server.return_value = [
            {"id": "ccn1-0001",
             "role": "MANAGEMENT-ROLE"
             },
           ]
        mocked_get_hostname.return_value = 'cs-ccp-mgmt-m1-clm'
        args = ('', 'Auth Failure because of wrong password', 1,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        mocked_psscript.return_value = resp
        self.assertRaises(exception.HyperVPSScriptError,
                          hyperv_utilities.get_host_validation_data, context)
        mocked_execute.assert_called_once_with()
        mocked_get_server.assert_called_once_with('MANAGEMENT-ROLE')

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_remove_activation_script')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils._copy_ps_script')
    def test__execute_script(self, m_copy, m_remove, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        resp_std_out = """{"iSCSI_initiator_service_state": "True",
                           "valid_compute_name": "True",
                           "hostname": "WIN-4NAOV9N2DCH",
                           "os_version": {"Major": 6, "MajorRevision": 0,
                                          "MinorRevision": 0, "Build": 9600,
                                          "Minor": 3, "Revision": 0},
                           "ipaddresses": ["10.1.214.32", "169.254.247.161",
                                            "192.168.28.63", "127.0.0.1"],
                           "os_edition": {"number": 8,
                            "name":
                            "Microsoft Windows Server 2012 R2 Datacenter"},
                           "vm_count": 0}"""
        args = (resp_std_out, '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        m_ps_script.return_value = resp
        expected_output = {u'iSCSI_initiator_service_state': "True",
                           u'valid_compute_name': "True",
                           u'hostname': u'WIN-4NAOV9N2DCH',
                           u'os_version': {u'Major': 6, u'MajorRevision': 0,
                                           u'MinorRevision': 0, u'Build': 9600,
                                           u'Minor': 3, u'Revision': 0},
                           u'ipaddresses': [u'10.1.214.32', u'169.254.247.161',
                                            u'192.168.28.63', u'127.0.0.1'],
                           u'os_edition': {u'number': 8,
                                           u'name': u'Microsoft Windows Server'
                                                    u' 2012 R2 Datacenter'},
                           u'vm_count': 0}
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        actual_out = hyperv_utilities._execute_script()
        self.assertEquals(expected_output, actual_out)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_remove_activation_script')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils._copy_ps_script')
    def test__execute_script_ex2(self, m_copy, m_remove, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        resp_std_out = ["Invalid out1"]
        args = (resp_std_out, '', 0,)
        resp = Response(args)
        m_ps_script.return_value = resp
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        self.assertRaises(TypeError, hyperv_utilities._execute_script)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_remove_activation_script')
    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils._copy_ps_script')
    def test__execute_script_ex(self, m_copy, m_remove, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', 'Script Execution Failed', 1,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        m_ps_script.return_value = resp
        self.assertRaises(exception.HyperVPSScriptError,
                          hyperv_utilities._execute_script)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script_copy_file')
    def test_copy_as_script(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        m_ps_script.return_value = resp
        hyperv_utilities._script_path = "activation.ps1"
        hyperv_utilities._copy_ps_script()
        with open(hyperv_utils.SCRIPT_SRC, 'r') as fd:
            file_content = fd.read()
        final_script = constants.PS_SCRIPT_TO_STREAM_WRITE % {"file_name":
                                              hyperv_utils.SCRIPT_DEST}\
                       + file_content +\
                       constants.PS_SCRIPT_TO_REPLACE_N
        m_ps_script.assert_called_once_with(hyperv_utilities.session,
                                            final_script)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script_copy_file')
    def test_copy_as_script_ex(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', 'Some error', 1,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "activation.ps1"
        m_ps_script.return_value = resp
        self.assertRaises(exception.HyperVPSScriptError,
                          hyperv_utilities._copy_ps_script)
        with open(hyperv_utils.SCRIPT_SRC, 'r') as fd:
            file_content = fd.read()
        final_script = constants.PS_SCRIPT_TO_STREAM_WRITE % {"file_name":
                                              hyperv_utils.SCRIPT_DEST}\
                       + file_content +\
                       constants.PS_SCRIPT_TO_REPLACE_N
        m_ps_script.assert_called_once_with(hyperv_utilities.session,
                                            final_script)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_remove_activation_script(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', '', 0,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "activation.ps1"
        m_ps_script.return_value = resp
        hyperv_utilities._remove_activation_script()
        ps_script = hyperv_utilities._get_ps_script_to_remove_file()
        m_ps_script.assert_called_once_with(hyperv_utilities.session,
                                            ps_script)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_remove_activation_script_ex(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', 'Permission denied', 1,)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "activation.ps1"
        m_ps_script.return_value = resp
        hyperv_utilities._remove_activation_script()
        ps_script = hyperv_utilities._get_ps_script_to_remove_file()
        m_ps_script.assert_called_once_with(hyperv_utilities.session,
                                            ps_script)

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_run_ps_script_through_pywinrm')
    def test_check_hyperv_host_using_pywinrm(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = "C:\Users\ADMINI~1\
        AppData\Local\Temp\activation.ps1"
        ps_script = hyperv_utilities._get_ps_script_for_validations()
        hyperv_utilities._check_hyperv_host_using_pywinrm()
        m_ps_script.assert_called_once_with(ps_script)

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_run_ps_script_through_pywinrm')
    def test_check_hyperv_host_using_pywinrm_ex1(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        ps_script = hyperv_utilities._get_ps_script_for_validations()
        m_ps_script.side_effect = [exception.HyperVHostUnSupportedOSError]
        self.assertRaises(exception.HyperVHostUnSupportedOSError,
                          hyperv_utilities._check_hyperv_host_using_pywinrm)
        m_ps_script.assert_called_once_with(ps_script)

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_run_ps_script_through_pywinrm')
    def test_check_hyperv_host_using_pywinrm_ex2(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        ps_script = hyperv_utilities._get_ps_script_for_validations()
        m_ps_script.side_effect = [exception.PyWinRMAuthenticationError]
        self.assertRaises(exception.HyperVHostAuthenticationError,
                          hyperv_utilities._check_hyperv_host_using_pywinrm)
        m_ps_script.assert_called_once_with(ps_script)

    @mock.patch('eon.virt.hyperv.hyperv_utils.HyperVUtils.'
                '_run_ps_script_through_pywinrm')
    def test_check_hyperv_host_using_pywinrm_ex3(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        ps_script = hyperv_utilities._get_ps_script_for_validations()
        m_ps_script.side_effect = [exception.PyWinRMConnectivityError]
        self.assertRaises(exception.HyperVHostConnectivityError,
                          hyperv_utilities._check_hyperv_host_using_pywinrm)
        m_ps_script.assert_called_once_with(ps_script)

    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_connectivity_check(self, mocked_ps_script, mocked_pywinrm):
        cur_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": 5986
                              }
        update_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": "5986"
                              }
        hyperv_utilities = hyperv_utils.HyperVUtils(cur_data)
        mocked_pywinrm.assert_called_with(
            cur_data[constants.EON_RESOURCE_IP_ADDRESS],
            cur_data[constants.EON_RESOURCE_PORT],
            cur_data[constants.EON_RESOURCE_USERNAME],
            cur_data[constants.EON_RESOURCE_PASSWORD],)
        args = ('', '', 0,)
        resp = Response(args)
        mocked_ps_script.return_value = resp
        hyperv_utilities._connectivity_check(update_data, cur_data)
        mocked_pywinrm.assert_called_with(
            update_data[constants.EON_RESOURCE_IP_ADDRESS],
            update_data[constants.EON_RESOURCE_PORT],
            update_data[constants.EON_RESOURCE_USERNAME],
            update_data[constants.EON_RESOURCE_PASSWORD],)

    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    def test_connectivity_check_2(self, mocked_pywinrm):
        cur_data = {"ip_address": "12.12.12.69",
                    "username": "Administrator",
                    "password": "password",
                    "port": "5986"}
        update_data = {"name": "HypervCompute"}
        hyperv_utilities = hyperv_utils.HyperVUtils(cur_data)
        hyperv_utilities._connectivity_check(update_data, cur_data)
        mocked_pywinrm.assert_called_once_with(
            cur_data[constants.EON_RESOURCE_IP_ADDRESS],
            cur_data[constants.EON_RESOURCE_PORT],
            cur_data[constants.EON_RESOURCE_USERNAME],
            cur_data[constants.EON_RESOURCE_PASSWORD], )

    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_connectivity_check_ex(self, mocked_ps_script, mocked_pywinrm):
        cur_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": 5986
                              }
        update_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": "5986"
                              }
        hyperv_utilities = hyperv_utils.HyperVUtils(cur_data)
        mocked_pywinrm.assert_called_with(
            cur_data[constants.EON_RESOURCE_IP_ADDRESS],
            cur_data[constants.EON_RESOURCE_PORT],
            cur_data[constants.EON_RESOURCE_USERNAME],
            cur_data[constants.EON_RESOURCE_PASSWORD], )
        args = ('', '', 1,)
        resp = Response(args)
        mocked_ps_script.return_value = resp
        self.assertRaises(exception.HyperVPSScriptError,
                          hyperv_utilities._connectivity_check,
                          update_data, cur_data)
        mocked_pywinrm.assert_called_with(
            update_data[constants.EON_RESOURCE_IP_ADDRESS],
            update_data[constants.EON_RESOURCE_PORT],
            update_data[constants.EON_RESOURCE_USERNAME],
            update_data[constants.EON_RESOURCE_PASSWORD], )

    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_connectivity_check_ex2(self, mocked_ps_script, mocked_pywinrm):
        cur_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": 5986
                              }
        update_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": "5986"
                              }
        hyperv_utilities = hyperv_utils.HyperVUtils(cur_data)
        mocked_pywinrm.assert_called_with(
            cur_data[constants.EON_RESOURCE_IP_ADDRESS],
            cur_data[constants.EON_RESOURCE_PORT],
            cur_data[constants.EON_RESOURCE_USERNAME],
            cur_data[constants.EON_RESOURCE_PASSWORD],)
        mocked_ps_script.side_effect = [exception.PyWinRMAuthenticationError]
        self.assertRaises(exception.HyperVHostAuthenticationError,
                          hyperv_utilities._connectivity_check,
                          update_data, cur_data)
        mocked_pywinrm.assert_called_with(
            update_data[constants.EON_RESOURCE_IP_ADDRESS],
            update_data[constants.EON_RESOURCE_PORT],
            update_data[constants.EON_RESOURCE_USERNAME],
            update_data[constants.EON_RESOURCE_PASSWORD],)

    @mock.patch('eon.virt.hyperv.pywinrm.get_pywinrm_session')
    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_connectivity_check_ex3(self, mocked_ps_script, mocked_pywinrm):
        cur_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": 5986
                              }
        update_data = {"name": "hyperv-compute",
                              "ip_address": "12.12.12.69",
                              "username": "Administrator",
                              "password": "password",
                              "port": "5986"
                              }
        hyperv_utilities = hyperv_utils.HyperVUtils(cur_data)
        mocked_pywinrm.assert_called_with(
            cur_data[constants.EON_RESOURCE_IP_ADDRESS],
            cur_data[constants.EON_RESOURCE_PORT],
            cur_data[constants.EON_RESOURCE_USERNAME],
            cur_data[constants.EON_RESOURCE_PASSWORD],)
        mocked_ps_script.side_effect = [exception.PyWinRMConnectivityError]
        self.assertRaises(exception.HyperVHostConnectivityError,
                          hyperv_utilities._connectivity_check,
                          update_data, cur_data)
        mocked_pywinrm.assert_called_with(
            update_data[constants.EON_RESOURCE_IP_ADDRESS],
            update_data[constants.EON_RESOURCE_PORT],
            update_data[constants.EON_RESOURCE_USERNAME],
            update_data[constants.EON_RESOURCE_PASSWORD],)

    @mock.patch(
        'eon.virt.hyperv.hyperv_utils.HyperVUtils._validate_pywinrm_response')
    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_run_ps_script_through_pywinrm(self, m_ps_script, m_resp):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', '', 0,)
        resp = Response(args)
        m_ps_script.return_value = resp
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        ps_script = hyperv_utilities._get_ps_script_for_validations()

        hyperv_utilities._run_ps_script_through_pywinrm(ps_script)
        m_ps_script.assert_called_once_with(hyperv_utilities.session,
                                            ps_script)
        m_resp.assert_called_once_with(resp)

    @mock.patch('eon.virt.hyperv.pywinrm.run_ps_script')
    def test_run_ps_script_through_pywinrm_ex1(self, m_ps_script):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('', '', 1,)
        resp = Response(args)
        m_ps_script.return_value = resp
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        ps_script = hyperv_utilities._get_ps_script_for_validations()

        self.assertRaises(exception.HyperVPyWinRMExectionError,
                      hyperv_utilities._run_ps_script_through_pywinrm,
                          ps_script)
        m_ps_script.assert_called_once_with(hyperv_utilities.session,
                                            ps_script)

    def test_validate_pywinrm_response(self):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('True True', '', 0)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._validate_pywinrm_response(resp)

    def test_validate_pywinrm_response_ex1(self):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('True False', '', 0)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        self.assertRaises(exception.HyperVHostVirtualizationNotEnabledError,
                      hyperv_utilities._validate_pywinrm_response, resp)

    def test_validate_pywinrm_response_ex2(self):
        resource_inventory = fake_data.hyperv_resource_inventory
        args = ('False True', '', 0)
        resp = Response(args)
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        self.assertRaises(exception.HyperVHostUnSupportedOSError,
                      hyperv_utilities._validate_pywinrm_response, resp)

    @mock.patch('eon.virt.hyperv.pywinrm.run_cmd_low_level')
    def test_get_temp_location(self, mocked_cmd):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_cmd.return_value = ("C:\Users\ADMINI~1\AppData\Local\Temp",
                                   "", 0,)
        loc = hyperv_utilities.get_temp_location()
        self.assertEquals(loc, "C:\Users\ADMINI~1\AppData\Local\Temp")
        mocked_cmd.assert_called_once_with(hyperv_utilities.session,
                                   constants.CMD_SCRIPT_TO_GET_TEMP_LOC)

    @mock.patch('eon.virt.hyperv.pywinrm.run_cmd_low_level')
    def test_get_temp_location_ex1(self, mocked_cmd):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_cmd.return_value = ("",
                                   "", 1,)
        self.assertRaises(exception.HyperVPSScriptError,
                          hyperv_utilities.get_temp_location)
        mocked_cmd.assert_called_once_with(hyperv_utilities.session,
                                   constants.CMD_SCRIPT_TO_GET_TEMP_LOC)

    @mock.patch('eon.virt.hyperv.pywinrm.run_cmd_low_level')
    def test_get_temp_location_ex2(self, mocked_cmd):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_cmd.side_effect = [exception.PyWinRMAuthenticationError]
        self.assertRaises(exception.HyperVHostAuthenticationError,
                          hyperv_utilities.get_temp_location)
        mocked_cmd.assert_called_once_with(hyperv_utilities.session,
                                   constants.CMD_SCRIPT_TO_GET_TEMP_LOC)

    @mock.patch('eon.virt.hyperv.pywinrm.run_cmd_low_level')
    def test_get_temp_location_ex3(self, mocked_cmd):
        resource_inventory = fake_data.hyperv_resource_inventory
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        mocked_cmd.side_effect = [exception.PyWinRMConnectivityError]
        self.assertRaises(exception.HyperVHostConnectivityError,
                          hyperv_utilities.get_temp_location)
        mocked_cmd.assert_called_once_with(hyperv_utilities.session,
                                   constants.CMD_SCRIPT_TO_GET_TEMP_LOC)

    @mock.patch('eon.virt.hyperv.pywinrm.run_cmd_low_level')
    def test_get_script_dest_full_path(self, mocked_cmd):
        resource_inventory = fake_data.hyperv_resource_inventory
        mocked_cmd.return_value = ("C:\Users\ADMINI~1\AppData\Local\Temp",
                                   "", 0,)
        expected_path = "C:\Users\ADMINI~1\AppData\Local\Temp\\activation.ps1"
        hyperv_utilities = hyperv_utils.HyperVUtils(resource_inventory)
        hyperv_utilities._script_path = ""
        path = hyperv_utilities.script_path
        self.assertEquals(expected_path, path)
        mocked_cmd.assert_called_once_with(hyperv_utilities.session,
                                   constants.CMD_SCRIPT_TO_GET_TEMP_LOC)
