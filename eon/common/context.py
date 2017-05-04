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

from eon.openstack.common import context

from oslo_config import cfg

CONF = cfg.CONF


class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, auth_token=None, domain_id=None, domain_name=None,
                 user=None, tenant=None, is_admin=False, is_public_api=False,
                 read_only=False, show_deleted=False, request_id=None):
        """Stores several additional request parameters:

        :param domain_id: The ID of the domain.
        :param domain_name: The name of the domain.
        :param is_public_api: Specifies whether the request should be processed
                              without authentication.

        """
        self.is_public_api = is_public_api
        self.domain_id = domain_id
        self.domain_name = domain_name

        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user=user, tenant=tenant,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=show_deleted,
                                             request_id=request_id)

    def to_dict(self):
        return {'auth_token': self.auth_token,
                'user': self.user,
                'tenant': self.tenant,
                'is_admin': self.is_admin,
                'read_only': self.read_only,
                'show_deleted': self.show_deleted,
                'request_id': self.request_id,
                'domain_id': self.domain_id,
                'domain_name': self.domain_name,
                'is_public_api': self.is_public_api}

    @classmethod
    def from_dict(cls, values):
        values.pop('user', None)
        values.pop('tenant', None)
        return cls(**values)


def get_admin_context(show_deleted=False):
    auth_dict = context.get_admin_auth_info()
    _context = RequestContext(auth_token=auth_dict['auth_token'],
                             user=CONF.keystone_authtoken.admin_user,
                             tenant=CONF.keystone_authtoken
                             .admin_tenant_name,
                             is_admin=True,
                             show_deleted=show_deleted)
    return _context