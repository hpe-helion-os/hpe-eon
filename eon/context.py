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

from eon.openstack.common import uuidutils


class RequestContext(object):
    """
    Stores information about the security context under which the user
    accesses the system, as well as additional request information.
    """

    def __init__(self, auth_tok=None, user=None, tenant=None, roles=None,
                 is_admin=False, read_only=False, show_deleted=False,
                 service_catalog=None):
        self.auth_tok = auth_tok
        self.user = user
        self.tenant = tenant
        self.roles = roles or []
        self.read_only = read_only
        self._show_deleted = show_deleted
        self.request_id = uuidutils.generate_uuid()
        self.service_catalog = service_catalog
        self.is_admin = is_admin

    def to_dict(self):
        # NOTE(ameade): These keys are named to correspond with the default
        # format string for logging the context in eon.common
        return {
            'request_id': self.request_id,

            'user': self.user,
            'user_id': self.user,

            'tenant': self.tenant,
            'tenant_id': self.tenant,
            'project_id': self.tenant,

            'is_admin': self.is_admin,
            'read_deleted': self.show_deleted,
            'roles': self.roles,
            'auth_token': self.auth_tok,
            'service_catalog': self.service_catalog,
        }

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    @property
    def show_deleted(self):
        """Admins can see deleted by default"""
        if self._show_deleted or self.is_admin:
            return True
        return False
