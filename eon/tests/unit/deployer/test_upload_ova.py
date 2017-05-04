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
import mock
from pyVmomi import vim

from eon.deployer import upload_ova
from eon.tests.unit import base_test
from eon.tests.unit import fake_data
from eon.deployer import util

v_util = util.VMwareUtils

lease_obj = mock.Mock()


def _fake_Import_vapp(spec, datacenter_obj):
    lease_obj.state = "ready"
    return lease_obj


class TestOVAUploadManager(base_test.TestCase):
    def setUp(self):
        base_test.TestCase.setUp(self)
        self.session = fake_data.FakeVCSession()
        self.template_name = "hlm-shell-vm-3.0-dc1"
        self.template_location = "http://123/456"
        self.datastore = mock.Mock()
        self.host = {"name": "1"}
        self.cluster = {"resourcePool": mock.Mock()}
        self.datacenter = {"vmFolder": mock.Mock()}
        self.ova_upload_mgr = upload_ova.OVAUploadManager(
                                self.session,
                                self.template_name,
                                self.template_location,
                                self.datacenter,
                                self.cluster,
                                self.host, self.datastore)

    def test_upload_ova(self):
        vmdk_name, file_size = ("x.vmdk", 10)
        url, thumbprint = ("http://1/", "tp")
        mocked_ob = mock.Mock()
        mocked_ob.info = None
        with contextlib.nested(
            mock.patch.object(util.VMwareUtils, "get_template",
                              return_value=None),
            mock.patch.object(upload_ova, "get_read_iter_for_ova"),
            mock.patch.object(upload_ova, "get_ovf_descriptor"),
            mock.patch.object(upload_ova, "create_import_spec_params"),
            mock.patch.object(self.ova_upload_mgr, "get_vmdk_name_and_size"
                              ),
            mock.patch.object(self.ova_upload_mgr,
                              "create_and_wait_for_lease"),
            mock.patch.object(self.ova_upload_mgr, "get_vmdk_url"),
            mock.patch.object(upload_ova, "create_write_connection"),
            mock.patch.object(self.ova_upload_mgr, "image_transfer"),
            mock.patch.object(v_util, "get_template_ref")
                               ) as (get_template_m,
                                     get_read_m, get_ovf, create_imp_params,
                                     get_vmdk_name, create_lease,
                                     get_vmdk_url,
                                     create_conn, _, get_temp):
            create_lease.return_value = mocked_ob
            get_vmdk_name.return_value = (vmdk_name, file_size)
            get_vmdk_url.return_value = (url, thumbprint)
            self.ova_upload_mgr.upload_ova()
            get_template_m.assert_called_once_with(self.session,
                                                   self.template_name)
            get_read_m.assert_called_once_with(self.template_location, True)
            get_ovf.assert_called_once_with(get_read_m.return_value)
            create_imp_params.assert_called_once_with(self.template_name)
            create_conn.assert_called_once_with(url, 10, ssl_thumbprint="tp")
            get_temp.assert_called_once_with(self.session['si'].content,
                                             mocked_ob)

    def test_create_and_wait_for_lease(self):
        import_spec = mock.Mock()
        res_pool = mock.Mock()
        res_pool.ImportVApp = _fake_Import_vapp
        expected = lease_obj
        self.assertEqual(expected,
            self.ova_upload_mgr.create_and_wait_for_lease(res_pool,
                                                      import_spec))

    def test_get_ovf_descriptor(self):
        read_iter = ["a", "b", "c", "<?xml", "</Envelope>"]
        assert isinstance(
                          upload_ova.get_ovf_descriptor(read_iter),
                          str)

    def test_get_vmdk_url(self):
        lease_info = mock.Mock()
        device_url1 = mock.Mock()
        device_url1.disk = mock.Mock()
        device_url1.sslThumbprint = "tp"
        device_url1.url = "url"
        host = "host"
        lease_info.deviceUrl = [device_url1]
        expected = ('url', 'tp')
        self.assertEqual(expected,
                         self.ova_upload_mgr.get_vmdk_url(lease_info, host))

    def test_create_import_spec_params(self):
        expected_type = vim.OvfManager.CreateImportSpecParams
        assert isinstance(
            upload_ova.create_import_spec_params(self.template_name),
            expected_type)
