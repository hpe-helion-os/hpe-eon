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

CONDUCTOR_MANAGER_TOPIC = "eon.conductor_manager"
ONEVIEW_MANAGER_TOPIC = "eon.oneview_manager"


class BaseConstants(object):
    TYPE_KEY = "type"
    NAME_KEY = "name"
    IP_ADDRESS_KEY = "ip_address"
    PASSWORD_KEY = "password"
    RESOURCE_MGR_ID = "id"
    USERNAME_KEY = "username"
    PORT_KEY = "port"
    RUN_PLAYBOOK_KEY = "run_playbook"
    SUPPORTED_QUERY_PARAMS = [IP_ADDRESS_KEY,
                              NAME_KEY,
                              TYPE_KEY]


class ResourceManagerConstants(BaseConstants):
    VCENTER = "vcenter"
    SUPPORTED_TYPES = [VCENTER]
    CREATE_RES_MGR_ATTRS = [BaseConstants.TYPE_KEY,
                            BaseConstants.IP_ADDRESS_KEY,
                            BaseConstants.USERNAME_KEY,
                            BaseConstants.PASSWORD_KEY]
    UPDATE_RES_MGR_ATTRS = [BaseConstants.NAME_KEY,
                            BaseConstants.IP_ADDRESS_KEY,
                            BaseConstants.USERNAME_KEY,
                            BaseConstants.PASSWORD_KEY,
                            BaseConstants.PORT_KEY,
                            BaseConstants.RUN_PLAYBOOK_KEY]


class ResourceConstants(BaseConstants):
    ESXCLUSTER = "esxcluster"
    HYPERV = "hyperv"
    RHEL = "rhel"
    HLINUX = "hlinux"
    BAREMETAL = "baremetal"
    STATE_KEY = "state"
    IMPORTED = "imported"
    PROVISION_INIT = "provision-initiated"
    PROVISIONING = "provisioning"
    PROVISIONED = "provisioned"
    ACTIVATING = "activating"
    ACTIVATED = "activated"
    DEACTIVATING = "deactivating"
    MAC_ADDR = "mac_addr"
    ILO_IP = "ilo_ip"
    ILO_USER = "ilo_user"
    ILO_PASSWORD = "ilo_password"
    LIST_SUPPORTED_TYPES = "list_supported_types"
    SUPPORTED_TYPES = [ESXCLUSTER, RHEL, HLINUX]
    SUPPORTED_STATES = [IMPORTED, PROVISION_INIT, PROVISIONING, PROVISIONED,
                        ACTIVATING, ACTIVATED, DEACTIVATING]
    CREATE_SUPPORTED_TYPES = [RHEL, HLINUX, BAREMETAL]
    SUPPORTED_QUERY_PARAMS = [BaseConstants.IP_ADDRESS_KEY,
                              BaseConstants.NAME_KEY,
                              BaseConstants.TYPE_KEY,
                              LIST_SUPPORTED_TYPES,
                              STATE_KEY
                              ]
    UPDATE_RES_ATTRS = [BaseConstants.NAME_KEY, BaseConstants.IP_ADDRESS_KEY,
                        BaseConstants.USERNAME_KEY, BaseConstants.PASSWORD_KEY,
                        BaseConstants.PORT_KEY, MAC_ADDR, ILO_IP, ILO_USER,
                        ILO_PASSWORD]
    API_FILTER_KEYS = [BaseConstants.TYPE_KEY, STATE_KEY]
    CREATE_KVM_RES_ATTRS = [BaseConstants.NAME_KEY,
                            BaseConstants.IP_ADDRESS_KEY,
                            BaseConstants.USERNAME_KEY,
                            BaseConstants.PASSWORD_KEY, BaseConstants.TYPE_KEY]
    CREATE_BAREMETAL_RES_ATTRS = [BaseConstants.NAME_KEY,
                                  BaseConstants.IP_ADDRESS_KEY, MAC_ADDR,
                                  ILO_IP, ILO_USER, ILO_PASSWORD]
    PROVISION_RHEL_ATTRS = ["boot_from_san", "os_version", "property", "type"]
    PROVISION_HLINUX_ATTRS = ["boot_from_san", "property", "type"]
    NAME = "name"
    RESOURCE_MANAGER_INFO = "resource_manager_info"
    HLM_PROPERTIES = "hlm_properties"
    NETWORK_PROPERTIES = "network_properties"
    HOST_ADD = "add_host"
    HOST_REMOVE = "remove_host"

    ACTIVATE_PAYLOAD_ESX = {"network_properties": None,
                            "input_model": {"server_group": "RACK1"},
                            }

    ACTIVATE_PAYLOAD_HLINUX = {
                        "input_model": {"server_group": "", "nic_mappings": "",
                                        "server_role": ""},
                        }

    ACTIVATE_PAYLOAD_RHEL = {
                        "input_model": {"server_group": "", "nic_mappings": "",
                                        "server_role": ""},
                        "run_wipe_disks": False,
                        "skip_disk_config": False,
                        }

    ACTIVATE_PAYLOAD_HYPERV = {
                        "input_model": {"server_group": "",
                                        "server_role": ""},
                        }


class HLMCConstants():
    SERVER_ID = "id"
    SERVER_IPADDR = "ip-addr"
    SERVER_ROLE = "role"
    SERVER_GROUP = "server-group"


class NetworkDriverConstants():
    OVSVAPP_NETWORK_DRIVER = "ovsvapp"
    NOOP_NETWORK_DRIVER = "noop"
