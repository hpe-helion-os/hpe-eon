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

import requests
import six
import ssl
import tarfile
import urlparse

from oslo_vmware import rw_handles
from pyVmomi import vim
from threading import Thread
from time import sleep
from urllib3 import connection as httplib

from eon.common import exception
from eon.deployer import util
from eon.openstack.common import log
from oslo_concurrency import lockutils

LOG = log.getLogger(__name__)
v_util = util.VMwareUtils


def get_ovf_descriptor(read_iter):
    """
    Read in the OVF iterative obj
    """
    ovf_content = ""
    for chunk in read_iter:
        ovf_content += chunk
        if "</Envelope>" in ovf_content:
            break

    return ovf_content[ovf_content.index("<?xml"):
                       ovf_content.index("</Envelope>") + 11]


def read_in_chunks(f, read_byte_size=1024):
    while True:
        d = f.read(read_byte_size)
        if not d:
            break
        yield d


def create_import_spec_params(template_name, disk_type="thin"):
    spec_param = vim.OvfManager.CreateImportSpecParams()

    # set the name/disk provisoning type
    spec_param.diskProvisioning = disk_type
    spec_param.entityName = template_name
    return spec_param


def create_write_connection(url, file_size=None,
                            method=None,
                            cookies=None,
                            overwrite=None,
                            content_type=None,
                            cacerts=False,
                            ssl_thumbprint=None):
    """
    Create HTTP connection write to VMDK file.
    """
    LOG.debug("Creating https connection with vCenter")
    if not method:
        method = "POST"

    if not content_type:
        content_type = 'application/x-vnd.vmware-streamVmdk'
    _urlparse = urlparse.urlparse(url)
    scheme, netloc, path, _, query, _ = _urlparse
    if scheme == 'http':
        conn = httplib.HTTPConnection(netloc)
    elif scheme == 'https':
        conn = httplib.HTTPSConnection(netloc)
        cert_reqs = None

        # cacerts can be either True or False or contain
        # actual certificates. If it is a boolean, then
        # we need to set cert_reqs and clear the cacerts
        if isinstance(cacerts, bool):
            if cacerts:
                cert_reqs = ssl.CERT_REQUIRED
            else:
                cert_reqs = ssl.CERT_NONE
            cacerts = None
        conn.set_cert(ca_certs=cacerts, cert_reqs=cert_reqs,
                      assert_fingerprint=ssl_thumbprint)
    else:
        excep_msg = _("Invalid scheme: %s.") % scheme
        raise ValueError(excep_msg)

    if query:
        path = path + '?' + query
    conn.putrequest(method, path)
    try:
        headers = {'User-Agent': "EON"}
        if file_size:
            headers.update({'Content-Length': str(file_size)})
        if overwrite:
            headers.update({'Overwrite': overwrite})
        if cookies:
            headers.update({})
        if content_type:
            headers.update({'Content-Type': content_type})
        for key, value in six.iteritems(headers):
            conn.putheader(key, value)
        conn.endheaders()
        return conn
    except requests.RequestException as excep:
        excep_msg = ("Error occurred while creating HTTP connection "
                     "to write to VMDK file with URL = %s.") % url
        raise exception.UploadOVAFailure(error=excep)


def get_read_iter_for_ova(ovf_path, is_url):
    """
    Return the remote/local file iterator to read the data
    """
    try:
        if is_url:
            f = requests.get(ovf_path, stream=True)
            f.raise_for_status()
        else:
            f = open(ovf_path)
        return f
    except IOError:
        raise exception.UploadOVAFailure(("Couldn't find the template %s") %
                                         ovf_path)


def create_read_connection(read_iter, ova_file, is_url):
    """
    Creates a read connection for the OVA base image
    """
    if is_url:
        read_connection = rw_handles.ImageReadHandle(read_iter)
    else:
        # this has to be a fresh read, since tarfile needs a file
        # object starting from 0. Hence not using read_iter in the
        # case of local file.
        read_connection = open(ova_file)

    return read_connection


class OVAUploadManager(object):
    """OVA Upload manager class for uploading the OVA.
    """
    def __init__(self, session, template_name,
                 template_location,
                 datacenter,
                 cluster,
                 host,
                 datastore):
        self.session = session
        self.template_name = template_name
        self.location = template_location
        self.datacenter = datacenter
        self.cluster = cluster
        self.host = host
        self.datastore = datastore
        self._bytes_written = 0
        self.is_transfer_done = False

    @property
    def is_url(self):
        if "http" in self.location or "https" in self.location:
            return True

    def update_progress(self, lease, file_size):
        """
        Keeps the lease alive while the VMDK is being transferred.
        Monitors the self._bytes_written and finds out the progress
        """
        interval = 10
        while not self.is_transfer_done:
            try:
                progress = int(float(self._bytes_written) / file_size * 100)
                lease.HttpNfcLeaseProgress(progress)
                if (lease.state == vim.HttpNfcLease.State.done):
                    return

                LOG.debug("Bytes written %s", str(self._bytes_written))
                sleep(interval)
            except:
                return

    def get_vmdk_name_and_size(self, import_res):
        """
        Get the VMDK details from the result of import spec
        """
        pvm_obj = import_res.fileItem.pop()
        return pvm_obj.path, pvm_obj.size

    def create_and_wait_for_lease(self, resource_pool, import_spec):
        """
        lease state can be of the following:
            1. Initializing (Copies the VM configuration)
            2. Ready (The lease is ready and VMDK can be uploaded)
            3. Error (If the Vm already exists)
        """
        lease = resource_pool.ImportVApp(import_spec.importSpec,
                                         self.datacenter['vmFolder'])

        retry_count = 15
        delay = 5  # in secs
        count = 1
        LOG.info("Copying the VM configuration,"
                 "Waiting for lease to be ready...")
        while retry_count > count:
            if (lease.state == vim.HttpNfcLease.State.ready):
                LOG.info("Successfully received the lease.")
                return lease

            elif (lease.state == vim.HttpNfcLease.State.error):
                raise exception.UploadOVAFailure(error=(
                    "Unable to create the VM,"
                    "check if the VM already exists"))
            count += 1
            sleep(delay)

    def get_vmdk_url(self, lease_info, host):
        """
        Find the URL corresponding to a VMDK file in lease info
        """
        url = None
        ssl_tp = None
        for device_url in lease_info.deviceUrl:
            if device_url.disk:
                url = device_url.url.replace('*', host)
                ssl_tp = device_url.sslThumbprint
                if url:
                    return url, ssl_tp

        if not url:
            raise exception.UploadOVAFailure(error=(
                "Unable to find the URL to upload the OVA"))

    def transfer_vmdk(self, read_handle, write_handle):
        """
        Here's the actual VMDK transfer takes place.
        """
        LOG.info("Transferring the VMDK to vCenter...")
        for chunk in read_in_chunks(read_handle):
            self._bytes_written += len(chunk)
            write_handle.send(chunk)
        self.is_transfer_done = True
        LOG.info("The VMDK is successfully transfered to vCenter.")

    def image_transfer(self, read_conn, write_conn, vmdk_name,
                       file_size, lease):
        """
        Transfer the VMDK
        """
        with tarfile.open(mode="r|", fileobj=read_conn) as tar:
            for tar_info in tar:
                if vmdk_name and tar_info.name.startswith(vmdk_name):
                    extracted = tar.extractfile(tar_info)
                    keepalive_thread = Thread(target=self.update_progress,
                                              args=(lease, file_size))
                    keepalive_thread.start()
                    self.transfer_vmdk(extracted, write_conn)
                    keepalive_thread.join()

    def _upload_ova(self):
        ovf_manager = self.session['si'].content.ovfManager
        read_iter = get_read_iter_for_ova(self.location, self.is_url)
        ovfd = get_ovf_descriptor(read_iter)
        import_spec_params = create_import_spec_params(self.template_name)
        import_vm_result = ovf_manager.CreateImportSpec(ovfd,
                                            self.cluster['resourcePool'],
                                            self.datastore,
                                            import_spec_params)
        vmdk_name, file_size = self.get_vmdk_name_and_size(import_vm_result)
        lease = self.create_and_wait_for_lease(self.cluster['resourcePool'],
                                               import_vm_result)
        vm_ref = v_util.get_template_ref(self.session['si'].content, lease)
        url, thumbprint = self.get_vmdk_url(lease.info, self.host['name'])
        read_connection = create_read_connection(read_iter, self.location,
                                                 self.is_url)
        write_connection = create_write_connection(url, file_size,
                                                   ssl_thumbprint=thumbprint)
        try:
            self.image_transfer(read_connection, write_connection, vmdk_name,
                                file_size, lease)
            lease.HttpNfcLeaseComplete()
            LOG.debug("Marking %s as template" % self.template_name)
            vm_ref['obj'].MarkAsTemplate()
        except Exception as e:
            LOG.exception(e)
            LOG.error("Failed to transfer VMDK to the vCenter")
            lease.HttpNfcLeaseAbort()
            self.is_transfer_done = True
            raise e
        finally:
            read_iter.close()
            read_connection.close()

        return vm_ref

    def upload_ova(self):
        """
        Checks whether the template exists, if not
        uploads the OVA onto the cluster in the vCenter
        :return template object
        """
        with lockutils.lock(self.template_name, lock_file_prefix='upload_ova'):
            LOG.debug("Checking if the template %s exists"
                      % self.template_name)
            template = util.VMwareUtils.get_template(self.session,
                                                     self.template_name)

            if template:
                return template

            LOG.info("Preparing to upload the template '%s' to vCenter"
                     % self.location)
            return self._upload_ova()
