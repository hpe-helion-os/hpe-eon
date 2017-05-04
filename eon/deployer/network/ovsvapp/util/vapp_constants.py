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

# OVSVAPP PREFIX which will be appended with the OVSVAPP IP and will be used as
# OVSVAPP display name and OVSVAPP host name
OVS_VAPP_PREFIX = 'ovsvapp'
# OVSvAPP Identifier
OVS_VAPP_IDENTIFIER = 'hp-ovsvapp'
# OVSvAPP Version(Do change this version for every release)
OVS_VAPP_VERSION = '3.0'
# Warning Message
WARN_MESSAGE = ("WARNING:: NEVER EDIT THIS SECTION TO "
                "AVOID PROBLEM WHILE INSTALLING/UPDATING/DELETING OVSVAPP")
# OVSVAPP Annotation
OVS_VAPP_ANNOTATION = ("%s\nVersion %s\n\n%s") % (OVS_VAPP_IDENTIFIER,
                                                  OVS_VAPP_VERSION,
                                                  WARN_MESSAGE)
# Cloud network types
TYPE_VLAN = 'vlan'
TYPE_VXLAN = 'vxlan'
# Minimum supported esxi version.
# WARNING: We can't reduce the version below 5.0 .
# Then some of the API calls will become vulnerable.
MIN_SUPPORTED_VERSION = '5.1'
# Max DV Ports per vCenter
VC_MAX_PORTS = 30000
# Delay in waiting for shutdown
SHUTDOWN_RETRY_DELAY = 5
# Retry count for shutdown
SHUTDOWN_RETRY = 8
# Number of workers
# What is the right no of workers ?
WORKERS = 2
