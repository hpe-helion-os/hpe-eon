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

from oslo_vmware import vim_util

from eon.virt.vmware import constants


def create_data_object(client_factory, spec_name, **kwargs):
    factory = client_factory.create('ns0:%s' % spec_name)
    [setattr(factory, key, value) for key, value in kwargs.items()]
    return factory


def get_objects(vim, type_, properties_to_collect):
    return vim_util.get_objects(vim,
        type_, 500, properties_to_collect)


def _create_filter(vim, propertyFilterSpec, collector=None):
    """ Custom filter."""
    if collector:
        tcollector = collector
    else:
        tcollector = vim._service_content.propertyCollector
    return vim.CreateFilter(tcollector,
                             spec=propertyFilterSpec,
                             partialUpdates=False)


def create_filter(vim):
    prop_spec_map = constants.prop_spec_map
    property_filter_spec = _get_property_filter_spec(vim, prop_spec_map)
    _create_filter(vim, property_filter_spec)


def wait_for_updates_ex(vim,
                        version,
                        collector=None,
                        max_wait=85,
                        max_update_count=-1):
    """PropertyCollector.WaitForUpdatesEx
    """
    if collector:
        tcollector = collector
    else:
        tcollector = vim._service_content.propertyCollector

    args_dict = {'maxWaitSeconds': max_wait}
    if max_update_count > 0:
        args_dict['maxObjectUpdates'] = max_update_count

    waitopts = create_data_object(vim.client.factory,
                                  'WaitOptions', **args_dict)

    return vim.WaitForUpdatesEx(tcollector,
                                version=version,
                                options=waitopts)


def _get_property_filter_spec(vim, prop_spec_map=None):
    if not prop_spec_map:
        prop_spec_map = constants.prop_spec_map

    client_factory = vim.client.factory
    recur_trav_spec = vim_util.build_recursive_traversal_spec(client_factory)
    # Build the object spec
    object_spec = vim_util.build_object_spec(client_factory,
                                    vim.service_content.rootFolder,
                                    [recur_trav_spec])
    # Build property spec
    propertySpecList = []
    for prop_spec in prop_spec_map:
        propertySpec = vim_util.build_property_spec(client_factory,
                                type_=prop_spec,
                                properties_to_collect=prop_spec_map[prop_spec])
        propertySpecList.append(propertySpec)

    return vim_util.build_property_filter_spec(client_factory,
                                               property_specs=propertySpecList,
                                               object_specs=object_spec)


def retreive_vcenter_inventory(vim, prop_spec_map=None, max_objects=500):
    """gets the inventory for a vCenter."""
    property_filter_spec = _get_property_filter_spec(vim, prop_spec_map)
    options = vim.client.factory.create('ns0:RetrieveOptions')
    options.maxObjects = max_objects
    return vim.RetrievePropertiesEx(vim.service_content.propertyCollector,
                                    specSet=[property_filter_spec],
                                    options=options)
