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

import copy

vc_data = {'name': 'test_vc',
           'ip_address': '10.1.1.10',
           'username': 'admin',
           'password': 'password',
           'port': '443',
           'type': 'vcenter'}

vc_data1 = {'name': 'test_vc1',
            'ip_address': '10.1.1.40',
            'username': 'admin',
            'password': 'password',
            'port': '443',
            'type': 'vcenter'}

rsc_mgr_id = '305ff8ea-15ee-4401-ab1e-ff12623986de'
vc_data_uuid = {'name': 'test_vc_1',
                'ip_address': '10.1.1.20',
                'username': 'admin',
                'password': 'password',
                'port': '443',
                'type': 'vcenter',
                'id': rsc_mgr_id}

vc_data_uuid_update = copy.deepcopy(vc_data_uuid)
vc_data_uuid_update['name'] = 'test_vc2'
vc_data_uuid_update['port'] = '9443'
vc_data_uuid_update['username'] = 'admin2'
vc_data_uuid_update['password'] = 'password2'

scvmm_data = {'name': 'test_scvmm',
              'ip_address': '10.1.1.30',
              'username': 'admin_scvmm',
              'password': 'password',
              'port': '567',
              'type': 'scvmm'}

esxclust_data = {'name': 'cluster1',
                 'resource_mgr_id': rsc_mgr_id,
                 'type': 'esx_cluster',
                 'state': 'imported',
                 "port": "UNSET"}

rhel_data = {'name': 'RHNode1',
             'type': 'rhel',
             'state': 'imported',
             'ip_address': '10.1.1.50',
             'username': 'rhel_admin',
             'password': 'password',
             "port": "22"}

rhel_data1 = {'name': 'rhelnode_1',
              'type': 'rhel',
              'state': 'imported',
              'ip_address': '10.1.1.60',
              'username': 'admin_rhel',
              'password': 'password',
              "port": "22"}

rhel_data_update = copy.deepcopy(rhel_data)
rhel_data_update['name'] = 'RHNode2'
rhel_data_update['state'] = 'provisioned'
rhel_data_update['username'] = 'rhel_admin2'
rhel_data_update['password'] = 'password'
rhel_data_update['ip_address'] = '10.1.1.60'

rhel_prop_key = 'version'
rhel_prop_val = '7.0'
rhel_prop_val_update = '7.0'

vc_prop_key = 'version'
vc_prop_val = '5.0'
vc_prop_val_update = '7.0'

rhel_prop_key1 = 'server_role'
rhel_prop_val1 = 'NOV-RHEL'

vc_prop_key1 = 'server_role'
vc_prop_val1 = 'NOV-ESX'
