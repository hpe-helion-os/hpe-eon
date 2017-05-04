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

import pecan
from oslo_config import cfg

ID_VERSION1 = "v2"
CONF = cfg.CONF


def form_host_url_for_refs(resource=None, version=ID_VERSION1):
    """Return the HATEOAS-style return URI reference for this service."""
    ref = ['{base}/{version}'.format(base=pecan.request.host_url,
                                     version=version)]
    if resource:
        ref.append('/' + resource)
    return ''.join(ref)


def convert_resource_id_to_href(resource_name, resource_id):
    """Convert the resouce ID to a HATEOAS-style href with resource name."""
    if resource_id:
        resource = '{name}/{id}'.format(name=resource_name, id=resource_id)
    else:
        resource = '{name}/????'.format(name=resource_name)
    return form_host_url_for_refs(resource=resource)


def convert_resource_manager_to_href(res_id):
    return convert_resource_id_to_href("resource_mgmrs", res_id)


def convert_to_hrefs(fields):
    """Convert id's within a fields dict to HATEOAS-style hrefs."""
    if 'id' in fields:
        fields["rel"] = "self"
        fields['href'] = convert_resource_manager_to_href(
                                            fields['id'])
    return fields
