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
#

import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from eon.api.controllers import base
from eon.api.controllers import link
from eon.api.controllers.v2.resource_manager import ResourceManager
from eon.api.controllers.v2.resources import Resources


class MediaType(base.APIBase):
    """A media type representation."""

    base = wtypes.text
    type = wtypes.text

    def __init__(self, base, type_):
        self.base = base
        self.type = type_


class V2(base.APIBase):
    """The representation of the version 2 of the API."""

    id = wtypes.text
    "The ID of the version, also acts as the release number"

    media_types = [MediaType]
    "An array of supported media types for this version"

    links = [link.Link]
    "Links that point to a specific URL for this version and documentation"

    resource_mgrs = [link.Link]
    "Links to the resource manager resource"

    resources = [link.Link]

    @classmethod
    def convert(self):
        v2 = V2()
        v2.id = "v2"
        v2.links = [link.Link.make_link('self', pecan.request.host_url,
                                        'v2', '', bookmark=True),
                    link.Link.make_link('describedby',
                                        '',
                                        'eon',
                                        'api-spec-v1.html',
                                        bookmark=True, type='text/html')]

        v2.media_types = [MediaType('application/json',
                                    'application/vnd.eon.v2+json')]

        v2.resource_mgrs = [link.Link.make_link('self', pecan.request.host_url,
                                                'v2', "resource_mgrs",
                                                bookmark=True),
                           ]
        v2.resources = [link.Link.make_link('self', pecan.request.host_url,
                                            'v2', "resources",
                                            bookmark=True),
                           ]

        return v2


class V2Controller(rest.RestController):
    """Version 2 API controller root."""
    resource_mgrs = ResourceManager()
    resources = Resources()

    @wsme_pecan.wsexpose(V2)
    def get(self):
        # NOTE: The reason why convert() it's being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return V2.convert()


__all__ = V2Controller
