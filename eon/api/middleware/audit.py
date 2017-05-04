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

from keystonemiddleware import audit

from eon.common import utils


class AuditMiddleware(audit.AuditMiddleware):
    """A wrapper on keystonemiddleware.audit.AuditMiddleware"""

    def __init__(self, app, public_routes, **conf):
        self._public_route = public_routes
        super(AuditMiddleware, self).__init__(app, **conf)

    def __call__(self, env, start_response):
        """Overrides the __call__ in keystonemiddleware.audit.AuditMiddleware
        """
        path = utils.safe_rstrip(env.get('PATH_INFO'), '/')

        # This check ignores auditing for the GET calls to (/, /v1 ,/v2) urls
        if path in self._public_route:
            return self._application(env, start_response)

        return super(AuditMiddleware, self).__call__(env, start_response)
