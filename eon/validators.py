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

import abc
import six
import uuid

from eon.common import exception
from eon.common.constants import ResourceManagerConstants as const
from eon.common.constants import ResourceConstants as res_const


def assert_is_valid_uuid_from_uri(_uuid):
    """Checks if the given string is actually a valid UUID
    :param _uuid: a valid/invalid UUID
    :raises: exception.InvalidUUIDInURI
    """
    try:
        uuid.UUID(_uuid)
    except ValueError:
        raise exception.InvalidUUIDInURI(uuid=_uuid)


@six.add_metaclass(abc.ABCMeta)
class ValidatorBase(object):
    """Base class for API validators."""

    def validate(self, json_data):
        """Validate the input JSON.
        :param json_data: JSON to validate against this class' internal schema.
        :returns: dict -- JSON content, post-validation and
        :                 normalization/defaulting.
        :raises: ValidationError
        """
        pass

    def validate_type(self, type_, supported_types):
        if type_ not in supported_types:
            raise exception.Invalid(_("Type %s is either "
                                      "invalid or not supported")
                                    % type_)

    def validate_all_keys(self, passed_params, required_params):
        if set(required_params) - set(passed_params):
            msg = _("Required parameters are not passed. "
                    "Mandatory keys are %s" % required_params)
            raise exception.InsufficientParamsError(msg=msg)

    def validate_keys_present(self, passed_params, available_params):
        if not set(passed_params) <= set(available_params):
            msg = _("Required parameters are not passed. "
                    "Available keys are %s" % available_params)
            raise exception.InsufficientParamsError(msg=msg)

    def _check_if_str(self, obj):
        if not isinstance(obj, basestring):
            raise exception.InvalidStringError(
                err=_("Not a 'string'"), string=obj)

    def _check_if_bool(self, obj):
        if not isinstance(obj, bool):
            raise exception.InvalidBoolError(
                err=_("Not a 'boolean'"), bool_=obj)

    def _check_if_not_null_str(self, obj):
        self._check_if_str(obj)

        if obj.strip() == "":
            raise exception.InvalidStringError(
                err=_("Cannot be empty"), string=obj)

    def validate_id(self, id_):
        try:
            self._check_if_not_null_str(id_)
        except exception.InvalidStringError as exc:
            raise exception.InvalidIdError(err=exc.message)

    def validate_name(self, name):
        try:
            self._check_if_not_null_str(name)
        except exception.InvalidStringError as exc:
            raise exception.InvalidNameError(err=exc.message)

    def validate_username(self, username):
        try:
            self._check_if_not_null_str(username)
        except exception.InvalidStringError as exc:
            raise exception.InvalidUsernameError(err=exc.message)

    def validate_password(self, password):
        try:
            self._check_if_not_null_str(password)
        except exception.InvalidStringError as exc:
            raise exception.InvalidPasswordError(err=exc.message)

    def validate_ip_address(self, ip_address):
        try:
            self._check_if_not_null_str(ip_address)
        except exception.InvalidStringError as exc:
            raise exception.InvalidIPAddressError(err=exc.message)

    def validate_port(self, port):
        if not port:
            raise exception.InvalidStringError(
                err=_("Cannot be empty"), string=port)

    def validate_query_params(self, query_params_dict,
                              supported_query_params):
        for key_ in six.iterkeys(query_params_dict):
            if key_ not in supported_query_params:
                msg = _("Invalid parameter '%s' passed for querying") % key_
                raise exception.Invalid(msg)

    def validate_keys_for_type(self, type_, data):
        _keys = data.keys()
        if type_ == res_const.RHEL:
            self.validate_keys_present(_keys, res_const.PROVISION_RHEL_ATTRS)
            return

        for param in _keys:
            if param in (list(set(res_const.PROVISION_RHEL_ATTRS) -
                              set(res_const.PROVISION_HLINUX_ATTRS))):
                msg = _("Invalid parameter (%s) passed for type %s" %
                        (param, type_))
                raise exception.Invalid(msg=msg)


class ResourceManagerValidator(ValidatorBase):
    """
    Validator for resource manager API
    """

    def validate_post(self, json_body):
        """
        :raises
            InvalidIdError,
            InvalidNameError,
            InvalidUsernameError,
            InvalidPasswordError,
            InvalidIPAddressError,
            InvalidPortError,
        """
        payload_keys = six.viewkeys(json_body)
        self.validate_all_keys(payload_keys,
                               const.CREATE_RES_MGR_ATTRS)
        self.validate_ip_address(json_body[const.IP_ADDRESS_KEY])
        if json_body.get(const.NAME_KEY):
            self.validate_name(json_body[const.NAME_KEY])
        if json_body.get(const.PORT_KEY):
            self.validate_port(json_body[const.PORT_KEY])
        self.validate_password(json_body[const.PASSWORD_KEY])
        self.validate_username(json_body[const.USERNAME_KEY])
        self.validate_type(json_body[const.TYPE_KEY], const.SUPPORTED_TYPES)

    def validate_put(self, json_body):
        """
        :raises
            InvalidIdError,
            InvalidNameError,
            InvalidUsernameError,
            InvalidPasswordError,
            InvalidIPAddressError,
            InvalidPortError,
        """
        payload_keys = six.viewkeys(json_body)
        self.validate_keys_present(payload_keys, const.UPDATE_RES_MGR_ATTRS)
        if json_body.get(const.IP_ADDRESS_KEY):
            self.validate_ip_address(json_body[const.IP_ADDRESS_KEY])
        if json_body.get(const.NAME_KEY):
            self.validate_name(json_body[const.NAME_KEY])
        if json_body.get(const.PORT_KEY):
            self.validate_port(json_body[const.PORT_KEY])
        if json_body.get(const.PASSWORD_KEY):
            self.validate_password(json_body[const.PASSWORD_KEY])
        if json_body.get(const.USERNAME_KEY):
            self.validate_username(json_body[const.USERNAME_KEY])

    def validate_get(self, kws):
        """
        :raises
            exception.Invalid
        """
        self.validate_query_params(kws,
                                   const.SUPPORTED_QUERY_PARAMS)
        self.validate_type(kws[const.TYPE_KEY], const.SUPPORTED_TYPES)


class ResourceValidator(ValidatorBase):

    def validate(self, json_data):
        pass

    def validate_get(self, kws):
        self.validate_query_params(kws,
                                   res_const.SUPPORTED_QUERY_PARAMS)
        if kws.get(res_const.TYPE_KEY):
            self.validate_type(kws[res_const.TYPE_KEY],
                               res_const.SUPPORTED_TYPES)
        if kws.get(res_const.STATE_KEY):
            self.validate_state(res_const.SUPPORTED_STATES,
                                kws[res_const.STATE_KEY])

    def validate_post(self, json_body):
        self.validate_type(json_body[const.TYPE_KEY],
                           res_const.CREATE_SUPPORTED_TYPES)
        payload_keys = six.viewkeys(json_body)
        type_ = json_body[const.TYPE_KEY]
        if type_ == res_const.BAREMETAL:
            # validate parameters for baremetal resource type
            self.validate_all_keys(payload_keys,
                                   res_const.CREATE_BAREMETAL_RES_ATTRS)
        else:
            # validate parameters for rhel and hlinux resource types
            self.validate_all_keys(payload_keys,
                                   res_const.CREATE_KVM_RES_ATTRS)
            for param in payload_keys:
                if param in list(set(res_const.CREATE_BAREMETAL_RES_ATTRS) -
                                 set(res_const.CREATE_KVM_RES_ATTRS)):
                    msg = _("Invalid parameter (%s) passed for type %s" %
                            (param, type_))
                    raise exception.Invalid(msg=msg)

    def validate_state(self, expected_states, observed_state):
        if observed_state not in expected_states:
            raise exception.InvalidStateError(observed=observed_state,
                                              expected=expected_states)

    def validate_put(self, json_body):
        """
        :raises
            InvalidIdError,
            InvalidNameError,
            InvalidUsernameError,
            InvalidPasswordError,
            InvalidIPAddressError,
        """
        payload_keys = six.viewkeys(json_body)
        self.validate_keys_present(payload_keys, res_const.UPDATE_RES_ATTRS)
        if json_body.get(const.IP_ADDRESS_KEY):
            self.validate_ip_address(json_body[const.IP_ADDRESS_KEY])
        if json_body.get(const.USERNAME_KEY):
            self.validate_name(json_body[const.USERNAME_KEY])
        if json_body.get(const.PASSWORD_KEY):
            self.validate_password(json_body[const.PASSWORD_KEY])
        if json_body.get(const.USERNAME_KEY):
            self.validate_username(json_body[const.USERNAME_KEY])
