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
import eventlet
from copy import deepcopy
from oslo_config import cfg

import eon.db
from eon.common import exception
from eon.common.constants import ResourceConstants as res_const
from eon.virt.common import utils as vir_utils
from eon.common import utils
from eon.common import message_notifier
from eon.openstack.common.gettextutils import _
from eon.hlm_facade.hlm_facade_handler import HLMFacadeWrapper
from eon.hlm_facade import exception as facade_excep
from eon.openstack.common import log as logging
from eon.validators import ResourceValidator
from eon.virt import constants as eon_const

from eon.virt import driver


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def _make_response(db_data,
                   property_list=[],
                   session=None,
                   inventory=None,
                   meta_data=True,
                   context=None):
    """Return the eon resource manager/resource info as response.

    :param db_data: a dict containing resource manager/resource info
        from vcenter table
    :param property_list: a list of dicts if passed is the
        meta/properties info of the eon_resource else if None then
        all properties of the eon_resource is collected from DB.
        This value is referred from response through key
        EON_RESOURCE_META_KEY
    :param session: DB session.
    :param response_attrs: a tuple containing all the attributes of
        the resource manager/resource
    :return a dict containing all the info of the resource manager/resource
        including its properties.

    sample response:
     { "id": "id1",
        "name": "resource_name",
        "ip_address" : "10.1.214.30
        "username": "root"
        "password": "password"
        "port" : "443"
        "meta_data": [{"name": "clutser_moid",
                      "id": "propety_id",
                      "value": "moid_value"
                     }]
        "inventory": {inventory}
     }
    """
    # Taking required attributes from db entry of eon_resource.
    resp = {}
    prop_list = []

    for key in eon_const.EON_RESOURCE_RESPONSE_ATTRS_FROM_DB:
        if db_data.get(key):
            resp[key] = db_data[key]

    if meta_data:
        # Getting properties
        if not property_list:
            property_list = []

            db_api = eon.db.get_api()
            db_api.setup_db_env()
            property_list = db_api.get_properties(
                context,
                db_data['id'],
                session)

        for pty in property_list:
            property_dict = dict()
            if not pty.get("key"):
                continue
            property_dict['name'] = pty['key']
            property_dict['value'] = pty['value']
            property_dict['id'] = pty['id']
            prop_list.append(property_dict)

        resp[eon_const.EON_RESOURCE_META_KEY] = prop_list

    if inventory:
        resp['inventory'] = inventory
    return resp


def _validate_duplicate_names(res_data, name, _id=None):
    """Checks if updated name already exists for different
    resource manager or newly created resource-manager's name
    already exist"""
    if _id:
        for data in res_data:
            if data.get("name") == name and data.get("id") != _id:
                return False
        return True
    else:
        for data in res_data:
            if data.get("name") == name:
                return False
        return True


def _validate_create(context, db_api, create_data, model_name):
    """ Validates the resource manager before creating it."""
    ipaddrlist = utils.get_addresses(create_data['ip_address'])

    if not ipaddrlist:
        errors = (_("Failed to register (%s)" +
                    ". The (%s) IP Address (%s) could not "
                    "be resolved.")
                  % (model_name, model_name, create_data['ip_address']))
        raise exception.AddressResolutionFailure(reason=errors)
    LOG.info("IP/FQDN for the " + model_name + " %s is %s" % (
        create_data['ip_address'],
        ipaddrlist))
    try:
        get_all = getattr(db_api, "get_all_%ss" % model_name)
        res_data = get_all(context)
        if not res_data:
            # No registered resources
            LOG.info("No registered %s" % model_name)
            return
    except Exception:
        errors = (_("Failed to retrieve data for (%s) %s")
                  % (model_name, create_data.get('ip_address')))
        raise exception.InternalFailure(reason=errors)
    name = create_data.get("name")
    valid_name = _validate_duplicate_names(res_data, name)
    if not valid_name:
        msg = (_("Two different (%s) with same "
                 "name cannot be registered") % model_name)
        raise exception.ResourceExists(reason=msg)
    registered_data = []
    for data in res_data:
        registered_data.append(data['ip_address'])

    if set(ipaddrlist).intersection(set(registered_data)):
        errors = (_("(%s) by ip_address (%s) already exists.")
                  % (model_name, create_data['ip_address']))
        raise exception.ResourceExists(reason=errors)


def _validate_update(context, db_api, update_data, _id,
                     model_name):
    get_resource = getattr(db_api, "get_%s" % model_name)
    res_data = get_resource(context, _id)
    if not res_data:
        errors = (_("(%s) with id [%s] does"
                    " not exist") % (model_name, _id))
        raise exception.ResourceNotFound(reason=errors)
    get_all = getattr(db_api, "get_all_%ss" % model_name)
    res_all_data = get_all(context)
    if not res_all_data:
        # This should not happen
        errors = (_("Could not retrieve (%s) %s")
                  % (model_name, update_data.get('ip_address')))
        raise exception.InternalFailure(reason=errors)
    name = update_data.get("name")
    if name:
        validate_name = _validate_duplicate_names(
            res_all_data, name, _id)
        if not validate_name:
            msg = (_("Update Failed since (%s) with"
                     " given name already exists") % model_name)
            raise exception.ResourceExists(reason=msg)
    if not update_data.get('ip_address'):
        return
    if res_data['ip_address'] == update_data.get('ip_address'):
        return
    # Check if the IP is being changed, in this case additional
    # validation to check if there is already a resource with the
    # information same as the updation data provided

    ipaddrlist = utils.get_addresses(update_data['ip_address'])
    if not ipaddrlist:
        errors = (_("Failed to update (%s)" +
                    ". The (%s) IP Address (%s) could not "
                    "be resolved.")
                  % (model_name, model_name, update_data['ip_address']))
        raise exception.AddressResolutionFailure(reason=errors)
    # Check if there is another resource registered with the same
    # information as the modified data
    registered_data = []
    for data in res_all_data:
        if data['id'] != _id:
            registered_data.append(data['ip_address'])
    LOG.info(registered_data)
    LOG.info(ipaddrlist)
    duplicates = set(ipaddrlist).intersection(set(registered_data))
    if duplicates:
        errors = (_("Update of (%s) failed: " +
                    "(%s) (%s) already exists.") %
                 (model_name, model_name, update_data['ip_address']))
        raise exception.ResourceExists(reason=errors)


class ResourceManager:

    """Implements Resource Manager CRUD API's"""

    def __init__(self):
        self.db_api = eon.db.get_api()
        self.db_api.setup_db_env()

    def start(self, context):
        db_resource_mgrs_data = self.db_api.get_all_resource_managers(
            context)
        for db_resource_mgr_data in db_resource_mgrs_data:
            driver_obj = driver.load_resource_mgr_driver(
                db_resource_mgr_data['type'])
            driver_obj.monitor_events(db_resource_mgr_data)

    def get_all(self, context, type_):
        """Get all EON resource mgrs of specified type.

        :param context: Request context.
        :param type_: type of eon resource mgrs which we want to retrieve.
            "None" for all resources.
        sample output:
            [
                {"id" : "resource_mgr_id1",..},
                {"id" : "resource_mgr_id2",..},
            ]
        """
        types = None
        if type_ and isinstance(type_, basestring):
            types = type_.strip(",").split(",")

        try:
            db_resource_mgrs_data = self.db_api.get_all_resource_managers(
                context, types=types)

            _resource_mgrs_data = []
            for db_resource_mgr_data in db_resource_mgrs_data:
                _resource_mgrs_data.append(_make_response(
                    db_resource_mgr_data))
        except Exception as e:
            msg = ("Error retrieving the 'resource managers' reason : %s"
                  % e.message)
            LOG.exception(msg)
            raise exception.RetrieveException(e.message)
        return _resource_mgrs_data

    def get(self, context, id_):
        """Get EON resource mgr having the specified unique id.

        :param context: Request context.
        :param id_: unique id of the eon resource mgr which we want to
            retrieve.
        """
        try:
            db_resource_mgr_data = self.db_api.get_resource_manager(
                context, id_)
            _resource_mgr_data = _make_response(db_resource_mgr_data)

        except exception.NotFound as e:
            raise e

        except Exception as e:
            LOG.exception(e)
            msg = ("Error retrieving the 'resource manager': %s."
                     " Reason: %s") % (id_, e.message)
            LOG.error(msg)
            raise exception.RetrieveException(e.message)

        LOG.info("eon resource_manager data is %s " %
                 logging.mask_password(_resource_mgr_data))
        return _resource_mgr_data

    def get_with_inventory(self, context, id_):
        """Get EON resource manager data along with inventory of the resource,
        identified by the unique id.

        :param context: Request context.
        :param type_: unique id of the eon resource manager which we want to
            retrieve.
        :param addn_data: additional data, as dict, which is needed for
            the inventory collection.
        """
        try:
            db_resource_mgr_data = self.db_api.get_resource_manager(
                context, id_)
            db_props_data = self.db_api.get_resource_mgr_properties(context,
                id_, key=eon_const.RESOURCE_MGR_STATE_KEY)

            driver_obj = driver.load_resource_mgr_driver(
                db_resource_mgr_data['type'])
            inventory = driver_obj.get_inventory(db_resource_mgr_data)
            resource_mgr_data = _make_response(db_resource_mgr_data,
                                                property_list=db_props_data,
                                                inventory=inventory)
            LOG.debug("[%s] Resource data %s"
                      % (id_, logging.mask_password(resource_mgr_data)))
            return resource_mgr_data

        except exception.NotFound as e:
            LOG.error(e)
            raise e
        except Exception as e:
            msg = "Error retrieving the 'resource':%s. Reason: %s" % (
                id_, e.message)
            LOG.exception(msg)
            raise exception.RetrieveException(e.message)

    def delete(self, context, id_):
        """Delete an EON resource mgr.

        :param context: Request context.
        :param id_: unique id of the eon resource mgr in DB.
        """
        try:
            db_resource_mgr_data = self.db_api.get_resource_manager(
                context, id_)
            act_res_data = self._get_resources(context,
                                               db_resource_mgr_data)
            for act in act_res_data:
                if act["state"] in [eon_const.EON_RESOURCE_STATE_ACTIVATED,
                                    eon_const.EON_RESOURCE_STATE_PROVISIONED]:
                    msg = _("Found resources in activated or provisioned "
                            "state")
                    raise exception.DeleteException(err=msg)

            _resource_data = _make_response(
                db_resource_mgr_data)
            LOG.info("Details for the ID %s is: %s" % (
                id_, logging.mask_password(_resource_data)))
            driver_obj = driver.load_resource_mgr_driver(
                db_resource_mgr_data['type'])
            driver_obj.validate_delete(db_resource_mgr_data)

            driver_obj.delete_vc_pass_through(context, db_resource_mgr_data)
            self.db_api.delete_resource_manager(context, id_)
        except exception.NotFound as e:
            msg = "Failed to delete resource manager %s. Error: %s" % (
                _resource_data.get('name'), e.message)
            LOG.exception(msg)
            raise e

    def auto_import_resources(self, context, _type):
        db_resource_mgrs_data = self.db_api.get_all_resource_managers(
            context, types=_type)
        for db_resource_mgr_data in db_resource_mgrs_data:
            try:
                db_rsrcs = self.db_api.get_all_resources(
                    context,
                    resource_mgr_id=db_resource_mgr_data['id'])
                db_resources_properties = {}
                for db_rsrc in db_rsrcs:
                    db_rsrc_properties = self.db_api.get_properties(
                        context, db_rsrc['id'])
                    db_resources_properties[db_rsrc['id']] = db_rsrc_properties
                driver_obj = driver.load_resource_mgr_driver(_type)
                driver_obj.auto_import_resources(context, db_resource_mgr_data,
                                                 db_rsrcs,
                                                 db_resources_properties)
            except Exception as exc:
                msg = ("Couldn't proceed with auto-import of resources "
                      "for resource_mgr %s") % db_resource_mgr_data['id']
                LOG.info(msg)
                LOG.exception("Error: %s" % exc)

    def create(self, context, data, is_auto_import=False):
        """Creates an EON resource mgr.
        Field "state" is introduced, will be set as "Registered".

        :param context: Request context.
        :param data: eon resource mgr data that is to be stored in DB.
        """
        db_session_event = 'create-resource_mgr'
        db_session = self.db_api.get_transactional_session(
            db_session_event)
        state_map = {eon_const.RESOURCE_MGR_STATE_KEY:
                        eon_const.EON_RESOURCE_MANAGER_STATE_REGISTERED}
        property_list = []
        try:
            _validate_create(context, self.db_api, data,
                             eon_const.EON_RESOURCE_MANAGER)
            resource_mgr_type = data.get('type')
            resource_mgr_driver = driver.load_resource_mgr_driver(
                resource_mgr_type)
            data = resource_mgr_driver.validate_create(context, data)

            LOG.info("Registering resource manager, context: %s",
                     logging.mask_password(data))
            db_resource_mgr_data = self.db_api.create_resource_manager(
                context, data, session=db_session)
            properties = resource_mgr_driver.get_properties(state_map)
            for property_key, property_value in properties.iteritems():
                property_list.append(
                    self.db_api.create_resource_mgr_property(
                    context, db_resource_mgr_data['id'],
                    property_key, property_value, session=db_session)
                )
            resource_mgr_dict = _make_response(db_resource_mgr_data,
                                               property_list=property_list)
            resource_mgr_driver.update_vc_pass_through(context,
                                                       resource_mgr_dict)
            self.db_api.commit_session(db_session_event, db_session)
            return resource_mgr_dict
        except (exception.AddressResolutionFailure,
                exception.InternalFailure,
                exception.ResourceExists,
                exception.UnsupportedVCenterVersion,
                exception.VCenterRegisterFailure
                ) as e:
            self.db_api.rollback_session('create-resource_mgr', db_session)
            msg = (_("Registering resource manager failed. Reason: '%s'")
                   % e.message)
            log_msg = (("Registering resource manager failed. Reason: '%s'")
                   % e.message)
            LOG.error(log_msg)
            raise exception.CreateException(msg=msg)
        except Exception as e:
            LOG.exception(e)
            self.db_api.rollback_session('create-resource_mgr', db_session)
            msg = (_("Registering resource manager failed. Reason: '%s'")
                   % e)
            log_msg = (("Registering resource manager failed. Reason: '%s'")
                   % e)
            LOG.error(log_msg)
            raise exception.CreateException(msg=msg)

    def _get_resources(self, context, resource_mgr_data, state=None):
        resources_data = []
        db_rsrcs = self.db_api.get_all_resources(
            context,
            resource_mgr_id=resource_mgr_data['id'],
            state=state)
        for db_rsrc in db_rsrcs:
            resource_data = {}
            resource_data['id'] = db_rsrc.id
            resource_data['name'] = db_rsrc.name
            resource_data['state'] = db_rsrc.state
            resource_data[res_const.RESOURCE_MANAGER_INFO] = (
                resource_mgr_data)
            resources_data.append(resource_data)
        return resources_data

    def update(self, context, id_, update_data):
        """Updates an EON resource mgr with the specified id.

        :param context: Request context.
        :param id_: unique id of the eon resource mgr in DB.
        :param update_data: a dictionary containing the updated values
            that is to be stored in DB.
        """
        run_playbook = update_data.get("run_playbook", True)

        try:
            _validate_update(context, self.db_api, update_data, id_,
                             eon_const.EON_RESOURCE_MANAGER)
            _resource_mgr_data = _make_response(
                self.db_api.get_resource_manager(context, id_))
            resource_mgr_type = _resource_mgr_data.get('type')
            resource_mgr_driver = driver.load_resource_mgr_driver(
                resource_mgr_type)

            if resource_mgr_type == eon_const.EON_RESOURCE_MGR_TYPE_VCENTER:
                name = update_data.get("name")
                if name and name != _resource_mgr_data.get("name"):
                    msg = (_("vCenter name cannot be updated"))
                    raise exception.UpdateException(msg=msg)

            _resource_mgr_data_update = deepcopy(_resource_mgr_data)
            _resource_mgr_data_update.update(update_data)
            LOG.info("Updating resource manager : %s",
                     logging.mask_password(_resource_mgr_data_update))

            _is_creds_changed = self._is_creds_changed(
                _resource_mgr_data, _resource_mgr_data_update)
            if _is_creds_changed:
                LOG.debug("[%s] Validating the updated credentials/Ip "
                          "address" % id_)
                resource_mgr_driver.validate_update(_resource_mgr_data_update,
                                                    _resource_mgr_data)
                # Gets the activated resources for the resource manager
                resources_data = self._get_resources(context,
                    _resource_mgr_data_update,
                    eon_const.EON_RESOURCE_STATE_ACTIVATED)

                resource_mgr_driver.update_vc_pass_through(
                    context, _resource_mgr_data_update)
                if resources_data and run_playbook:
                    self.db_api.update_resource_mgr_property(context,
                        "update_property",
                        id_, key=eon_const.RESOURCE_MGR_STATE_KEY,
                         value=eon_const.EON_RESOURCE_MANAGER_STATE_UPDATING)
                    eventlet.spawn_n(resource_mgr_driver.update,
                        context, id_, resource_inventory=resources_data)

            self.db_api.update_resource_manager(context, id_,
                                                _resource_mgr_data_update)
            props = self.db_api.get_resource_mgr_properties(context,
                id_, key=eon_const.RESOURCE_MGR_STATE_KEY)
            return _make_response(_resource_mgr_data_update,
                                  property_list=props)

        except Exception as e:
            LOG.exception(e)
            msg = (_("Updating resource manager failed. Reason: '%s'")
                   % e.message)
            log_msg = (("Updating resource manager failed. Reason: '%s'")
                   % e.message)
            LOG.error(log_msg)
            raise exception.UpdateException(msg=msg)

    def _is_creds_changed(self, curr_data, update_data):
        is_creds_changed = False
        for fl in eon_const.SUPPORTED_UPDATE_FIELDS:
            is_creds_changed = (is_creds_changed or
                                curr_data.get(fl) != update_data.get(fl))
        return is_creds_changed

    def update_property(self, context, rsrc_id, property_name,
                        property_value):
        pass


class Resource(object):

    """Implements Resource CRUD operations"""

    def __init__(self):
        self.db_api = eon.db.get_api()
        self.db_api.setup_db_env()
        self.validator = ResourceValidator()
        self.virt_utils = vir_utils.VirtCommonUtils()

    def get_all(self, context, filters=None):
        """Get all EON resources of specified type.

        :param context: Request context.
        :param filters: Dictionary of type and state of the resource
            {"type": "<resource type>",
             "state": "<resource state>"}
             <resource type>: type of eon resources which we want to retrieve.
                              esxcluster/hlinux/rhel
                              "None" for all resources.
             <resource state>: state of eon resource which we want to retrieve.
                               deactivating/activated/provisioned/imported/
                               "None" for all states.
        sample output:
            [
                {"id" : "resource1",..},
                {"id" : "resource2",..},
            ]
        """
        try:
            db_resources_data = self.db_api.get_all_resources(
                context, **filters)

            _resources_data = []
            for db_resource_data in db_resources_data:
                _resources_data.append(_make_response(db_resource_data))
        except Exception as e:
            msg = ("Error retrieving the 'resources' reason : %s"
                  % e.message)
            LOG.exception(msg)
            raise exception.RetrieveException(e.message)
        return _resources_data

    def get(self, context, id_):
        """Get EON resource having the specified unique id.

        :param context: Request context.
        :param id_: unique id of the resource which we want to
            retrieve.
        """
        try:
            db_resource_data = self.db_api.get_resource(
                context, id_)
            _resource_data = _make_response(db_resource_data,
                                            meta_data=False)

        except exception.NotFound as e:
            raise e

        except Exception as e:
            msg = ("Error retrieving the 'resource':%s. Reason: %s"
                  % (id_, e.message))
            LOG.exception(msg)
            raise exception.RetrieveException(e.message)

        LOG.info("Resource manager data is %s " %
                 logging.mask_password(_resource_data))
        return _resource_data

    def get_with_inventory(self, context, id_):
        """Get resource data along with inventory of the resource,
        identified by the unique id.

        :param context: Request context.
        :param id_: id of the resource
        :returns
            {username": "UNSET", "name": "", "ip_address": "UNSET",
            "res_mgr_details": {},
            "inventory":
                {"datacenter": {"moid": "datacenter-1", "name": "dc"}},
            "id": "",
            "password": "UNSET", "type": "esxcluster", "port": "UNSET"}
        """
        try:
            db_resource_data = self.db_api.get_resource(context, id_)
            res_properties = self.db_api.get_properties(context, id_)

            # for non resource managers return get
            if (db_resource_data['type'] !=
                    eon_const.EON_RESOURCE_TYPE_ESX_CLUSTER):
                return _make_response(db_resource_data)

            res_mgr_obj = (
                self.db_api.get_resource_managers_by_resource_id(context,
                                                                 id_))
            driver_obj = driver.load_resource_driver(db_resource_data['type'])
            _inventory = driver_obj.get_res_inventory(res_mgr_obj,
                                                      res_properties)
            _resource_data = _make_response(db_resource_data,
                                            inventory=_inventory)
            # (NOTE) Here setting the details of resource manager for the
            # resource
            _res_mgr_data = _make_response(res_mgr_obj, meta_data=False)
            _resource_data[eon_const.RSRC_MGR_INFO] = _res_mgr_data

        except exception.NotFound as e:
            LOG.exception(e)
            raise e
        except Exception as e:
            msg = _("Error retrieving the 'eon_resource':%s. Reason: %s") % (
                id_, e)
            log_msg = ("Error retrieving the 'eon_resource':%s."
                       " Reason: %s") % (id_, e)
            LOG.exception(log_msg)
            raise exception.RetrieveException(msg)

        LOG.info("The Resource data %s "
                 % logging.mask_password(_resource_data))
        return _resource_data

    def delete(self, context, id_):
        """Delete an EON resource.

        :param context: Request context.
        :param id_: unique id of the eon resource in DB.
        """
        try:
            db_resource_data = self.db_api.get_resource(
                context, id_)

            if db_resource_data['type'] == (eon_const.
                                            EON_RESOURCE_TYPE_ESX_CLUSTER):
                msg = _("Delete operation not supported for type %s"
                        % db_resource_data['type'])
                raise exception.DeleteException(err=msg)

            _resource_data = _make_response(
                db_resource_data)
            _resource_data_log = deepcopy(_resource_data)
            _resource_data_log.pop("meta_data", None)
            LOG.info("Details for the ID %s is: %s" % (
                id_, logging.mask_password(_resource_data_log)))
            driver_obj = driver.load_resource_driver(
                db_resource_data['type'])
            driver_obj.validate_delete(db_resource_data)
            driver_obj.delete(context, id_)
            self.db_api.delete_resource(context, id_)
            # delete the data from hlm input model
            try:
                LOG.info("[%s] remove resource from input model" % id_)
                hux_obj = HLMFacadeWrapper(context)
                resource_id = db_resource_data[eon_const.EON_RESOURCE_ID]
                hux_obj.delete_server(resource_id)
                hux_obj.commit_changes(resource_id, "Delete compute resource")
            except facade_excep.NotFound:
                # log and do nothing
                LOG.warn("[%s] resource not found in hlm input model" % id_)
            LOG.info("[%s]: Deleted resource from eon" % id_)
            # Notify the message to consumers
            try:
                message = {"resource_id": id_,
                    "resource_state": eon_const.EON_RESOURCE_STATE_REMOVED,
                    "resource_details": _resource_data,
                    }
                message_notifier.notify(context,
                                        message_notifier.EVENT_PRIORITY_INFO,
                                        message_notifier.EVENT_TYPE[
                                            'removed'],
                                        message)
            except Exception as ex:
                LOG.exception(
                    "Exception while notifying the message : %s" % ex)
        except exception.NotFound as e:
            msg = ("Failed to delete resource %s. Error: %s") % (
                _resource_data['name'], e.message)
            LOG.exception(msg)
            raise e

    def create(self, context, data):
        """Creates an EON resource.

        :param context: Request context.
        :param data: eon resource data that is to be stored in DB.
        """
        db_session_event = 'create-resource'
        db_session = self.db_api.get_transactional_session(
            db_session_event)
        try:
            _validate_create(context, self.db_api, data,
                             eon_const.EON_RESOURCE)
            resource_type = data.get('type')
            resource_driver = driver.load_resource_driver(
                resource_type)
            data = resource_driver.validate_create(context, data)

            LOG.info("Registering resource , context: %s",
                     logging.mask_password(data))
            db_resource_data = self.db_api.create_resource(context,
                                                           data,
                                                           session=db_session)
            properties = resource_driver.get_properties(data)
            for property_key, property_value in properties.iteritems():
                self.db_api.create_property(context,
                                            db_resource_data['id'],
                                            property_key,
                                            property_value,
                                            session=db_session)
            self.db_api.commit_session(db_session_event, db_session)
            resource_dict = _make_response(db_resource_data)
            return resource_dict
        except (exception.AddressResolutionFailure,
                exception.InternalFailure,
                exception.ResourceExists) as e:
            self.db_api.rollback_session('create-resource', db_session)
            msg = (_("Registering resource failed. Reason: '%s'")
                   % e.message)
            log_msg = (("Registering resource failed. Reason: '%s'")
                   % e.message)
            LOG.error(log_msg)
            raise exception.CreateException(msg=msg)
        except Exception as e:
            self.db_api.rollback_session('create-resource', db_session)
            msg = (_("Registering resource failed. Reason: '%s'")
                   % e)
            log_msg = (("Registering resource failed. Reason: '%s'")
                   % e)
            LOG.error(log_msg)
            raise exception.CreateException(msg=msg)

    def _get_state(self, context, id_):
        db_resource_data = self.db_api.get_resource(
            context, id_)
        return db_resource_data['state']

    def _pre_activation_steps(self, context, id_, resource_inventory, data):
        """
        Performs pre-activation checks
        """
        LOG.info("[%s] Pre-activation checks started" % id_)
        resource_type = resource_inventory[eon_const.EON_RESOURCE_TYPE]
        # allowed states for esxcluster
        expected_states = eon_const.EXPECTED_STATES_ACTIVATION[resource_type]

        self.validator.validate_state(
            expected_states,
            resource_inventory.get(eon_const.EON_RESOURCE_STATE))

        resource_driver = driver.load_resource_driver(
            resource_inventory[eon_const.EON_RESOURCE_TYPE])
        # Performing pre-activation steps
        if not data and (resource_type !=
                         eon_const.EON_RESOURCE_TYPE_ESX_CLUSTER):
            msg = (_("Config json parameter not found"
                     " for %s compute activation") % resource_type)
            id_ = resource_inventory.get("id")
            raise exception.ActivationFailure(resource_name=id_,
                                            err=msg)

        resource_driver.pre_activation_steps(context,
                                    resource_inventory=resource_inventory,
                                    data=data)

        LOG.info("[%s] Pre-activation checks finished successfully" % id_)
        next_state = eon_const.ACTIVATION_STATE_MAPPING.get(
            resource_inventory.get(eon_const.EON_RESOURCE_STATE))
        self.virt_utils.update_prop(context, id_, eon_const.EON_RESOURCE_STATE,
                                    next_state)
        resource_inventory[eon_const.EON_RESOURCE_STATE] = next_state

    def populate_network_json(self, context, type_, data):
        try:
            resource_driver = driver.load_resource_driver(type_)
            return resource_driver.populate_network_json(context, data)
        except Exception as e:
            raise exception.NetworkPropertiesJSONError(
                resource_type=type_,
                err=str(e.message))

    def _activate(self, context, id_, resource_inventory, data):
        """Runs the activation steps in an eventlet thread

        :param context: Request context.
        :param resource_inventory: eon resource data stored in DB.
        :param data: payload from API call
        """
        LOG.info("[%s] Activation started " % id_)
        resource_driver = driver.load_resource_driver(
            resource_inventory[eon_const.EON_RESOURCE_TYPE])
        try:
            run_playbook = data.get(eon_const.RUN_PLAYBOOK, True)
            input_model_data = data.get(eon_const.INPUT_MODEL)
            resource_driver.activate(context,
                                     id_,
                                     data,
                                     resource_inventory=resource_inventory,
                                     input_model_info=input_model_data,
                                     run_playbook=run_playbook)
            LOG.info("[%s] Activation finished successfully" % id_)
            try:
                message = {"resource_id": id_,
                    "resource_state": eon_const.EON_RESOURCE_STATE_ACTIVATED,
                    "resource_details": resource_inventory, }
                message_notifier.notify(context,
                                message_notifier.EVENT_PRIORITY_INFO,
                                message_notifier.EVENT_TYPE[
                                    eon_const.EON_RESOURCE_STATE_ACTIVATED],
                                message)
            except Exception as ex:
                LOG.exception(
                    "Exception while notifying the message : %s" % ex)
        except Exception as e:
            LOG.exception(e)
            try:
                self.db_api.delete_property(context, id_,
                                            eon_const.HYPERVISOR_ID)
            except exception.NotFound:
                pass  # ignore
            raise exception.ActivationFailure(
                resource_name=resource_inventory['id'],
                err=str(e.message))

    def activate(self, context, id_, data):
        """Activate starting point for a resource

        :param context: Request context.
        :param data: eon resource data that is to be stored in DB.
        """
        try:
            resource_inventory = self.get_with_inventory(context, id_)
            self.validator.validate_type(resource_inventory['type'],
                                     res_const.SUPPORTED_TYPES)
            self._pre_activation_steps(context, id_, resource_inventory, data)
            eventlet.spawn_n(self._activate,
                             context, id_, resource_inventory, data)
            return self.get(context, id_)
        except (exception.InvalidStateError, exception.NotFound) as e:
            raise exception.ActivationFailure(resource_name=id_,
                                              err=e.message)
        except Exception:
            rollback_state = (eon_const.ROLLBACK_STATE_ACTIVATION[
                                resource_inventory[
                                    eon_const.EON_RESOURCE_TYPE]])
            self.virt_utils.update_prop(context, id_,
                                        eon_const.EON_RESOURCE_STATE,
                                        rollback_state)
            raise

    def _pre_deactivation_steps(self, context, id_, data, resource_inventory):
        """
        updates the state and validates it
        """
        LOG.info("[%s] Pre deactivation checks started" % id_)
        resource_type = resource_inventory[eon_const.EON_RESOURCE_TYPE]
        expected_states = eon_const.EXPECTED_STATES_DEACTIVATION[resource_type]
        self.validator.validate_state(expected_states,
                                      resource_inventory.get(
                                        eon_const.EON_RESOURCE_STATE))
        resource_driver = driver.load_resource_driver(
                            resource_inventory[eon_const.EON_RESOURCE_TYPE])
        resource_driver.pre_deactivation_steps(context,
                                        resource_inventory=resource_inventory)
        next_state = eon_const.DEACTIVATION_STATE_MAPPING.get(
            resource_inventory.get(eon_const.EON_RESOURCE_STATE))

        self.virt_utils.update_prop(context, id_, eon_const.EON_RESOURCE_STATE,
                                    next_state)
        resource_inventory[eon_const.EON_RESOURCE_STATE] = next_state
        LOG.info("[%s] Pre deactivation checks finished successfully" % id_)

    def _forced_deactivate(self, context, id_, resource_inventory):
        """Forced deactivation tasks"""
        LOG.info("[%s] Forced deactivation tasks started" % id_)
        for prop in eon_const.DB_RESOURCE_PROP:
            try:
                self.db_api.get_properties(context, resource_inventory['id'],
                                       key=prop)
                self.db_api.delete_property(context, resource_inventory['id'],
                                        prop)
            except exception.NotFound:
                pass
        LOG.info("[%s] Forced deactivation finished successfully" % id_)

    def _deactivate(self, context, id_, data, resource_inventory):
        """
        Runs the deactivation steps in an eventlet thread
        """
        resource_driver = driver.load_resource_driver(
            resource_inventory[eon_const.EON_RESOURCE_TYPE])
        LOG.info("[%s] Deactivation started." % id_)
        try:
            # Notifies on deactivation
            self.notify(context, id_, resource_inventory)

            run_playbook = data.get(eon_const.RUN_PLAYBOOK, True)
            force_deactivate = data.get(eon_const.FORCED_KEY, False)
            resource_driver.deactivate(
                context, id_,
                resource_inventory=resource_inventory,
                run_playbook=run_playbook,
                force_deactivate=force_deactivate)
            resource_driver.post_deactivation_steps(context,
                resource_inventory=resource_inventory)
            LOG.info("[%s] Deactivation finished successfully" % id_)
        except Exception as e:
            LOG.exception(e)
            LOG.error("Deactivation observed failures. %s " %
                      e.message)
        finally:
            try:
                self.db_api.delete_property(context, id_,
                                            eon_const.HYPERVISOR_ID)
            except exception.NotFound:
                pass  # ignore
            if data.get(eon_const.FORCED_KEY):
                self._forced_deactivate(context, id_, resource_inventory)
            rollback_state = (eon_const.ROLLBACK_STATE_ACTIVATION[
                                resource_inventory[
                                    eon_const.EON_RESOURCE_TYPE]])
            self.virt_utils.update_prop(context, id_,
                                        eon_const.EON_RESOURCE_STATE,
                                        rollback_state)

    def deactivate(self, context, id_, data):
        """deactivates a resource.

        :param context: Request context.
        :param data: additional data passed during deactivation
        """
        try:
            resource_inventory = self.get_with_inventory(context, id_)
            if data.get(eon_const.FORCED_KEY):
                self.virt_utils.update_prop(context, id_,
                                            eon_const.EON_RESOURCE_STATE,
                                            res_const.DEACTIVATING)
            else:
                # Runs pre checks and updates the state
                self._pre_deactivation_steps(context, id_,
                                        data, resource_inventory)

            eventlet.spawn_n(self._deactivate,
                             context, id_, data,
                             resource_inventory)
            return self.get(context, id_)

        except (exception.NotFound,
                exception.InvalidStateError) as e:
            raise exception.DeactivationFailure(resource_name=id_,
                                                err=e.message)
        except Exception as e:
            self.virt_utils.update_prop(context, id_,
                                        eon_const.EON_RESOURCE_STATE,
                                        eon_const.EON_RESOURCE_STATE_ACTIVATED)
            LOG.exception(e.message)
            raise e

    def notify(self, context, id_, resource_inventory):
        try:
            message = {"resource_id": id_,
                       "resource_state": eon_const.EON_RESOURCE_STATE_IMPORTED,
                       "resource_details": resource_inventory,
                       }
            message_notifier.notify(context,
                                    message_notifier.EVENT_PRIORITY_INFO,
                                    message_notifier.EVENT_TYPE['deactivated'],
                                    message)
        except Exception as ex:
            LOG.exception("Exception while notifying the message : %s" % ex)

    def update(self, context, id_, update_data):
        """Updates an EON resource with the specified id.

        :param context: Request context.
        :param update_data: a dictionary containing the updated values
            that is to be stored in DB.
        """
        db_session_event = "update-resource"
        db_session = self.db_api.get_transactional_session(db_session_event)
        try:
            _validate_update(context, self.db_api, update_data, id_,
                             eon_const.EON_RESOURCE)
            db_resource_data = self.db_api.get_resource(context, id_)
            _resource_data_update = deepcopy(db_resource_data)
            resource_type = db_resource_data.get('type')
            if resource_type == eon_const.EON_RESOURCE_TYPE_ESX_CLUSTER:
                msg = _("Update option is not applicable for resource type %s"
                        % resource_type)
                raise exception.Invalid(msg)

            resource_driver = driver.load_resource_driver(resource_type)
            _resource_data_update.update(update_data)
            _is_creds_changed = self._is_creds_changed(
                db_resource_data, _resource_data_update)
            if _is_creds_changed:
                resource_driver.validate_update(context,
                                                db_resource_data,
                                                update_data)

            LOG.info("Updating resource, context: %s",
                     logging.mask_password(_resource_data_update))
            db_resource_data = self.db_api.update_resource(
                context, id_, _resource_data_update, session=db_session)

            if _is_creds_changed:
                resource_driver.update(context, db_resource_data, id_)

            self.db_api.commit_session(db_session_event, db_session)
            resource_dict = _make_response(db_resource_data)
            return resource_dict
        except Exception as e:
            self.db_api.rollback_session(db_session_event, db_session)
            msg = (_("Updating resource failed. Reason: '%s'")
                   % e.message)
            log_msg = (("Updating resource failed. Reason: '%s'")
                   % e.message)
            LOG.error(log_msg)
            LOG.exception(e)
            raise exception.UpdateException(msg=msg)

    def _is_creds_changed(self, curr_data, update_data):
        is_creds_changed = False
        for fl in eon_const.SUPPORTED_UPDATE_FIELDS:
            is_creds_changed = (is_creds_changed or
                                curr_data.get(fl) != update_data.get(fl))
        return is_creds_changed

    def _host_commission(self, context, id_, resource_inventory, data):
        resource_type = resource_inventory['type']
        failed = False
        vc_data = resource_inventory.get(eon_const.RSRC_MGR_INFO)
        resource_driver = driver.load_resource_driver(resource_type)
        network_prop = resource_driver.get_network_properties(context,
                                                            vc_data,
                                                            resource_inventory)

        # Provision compute and network proxy vm's
        hosts_data_info = resource_driver.host_commission(
            context,
            resource_type,
            resource_inventory,
            network_prop)
        run_playbook = data.get("run_playbook", True)

        try:
            resource_driver.host_commission_model_changes(
                context,
                id_,
                resource_inventory=resource_inventory,
                hosts_data=hosts_data_info,
                payload_data=data)
            LOG.info("[%s] Successfully completed host provisioning. " % id_)

        except Exception as e:
            resource_driver.roll_back_host_info(
                context, copy.deepcopy(hosts_data_info),
                resource_inventory)
            failed = True
            LOG.exception(e)

        # Move the host/hosts back to the cluster based on the status
        finally:
            try:
                # Ignore if user wants to run playbook manually
                if run_playbook:
                    resource_driver.move_hosts(id_, resource_inventory,
                                               hosts_data_info, failed)
            except:
                # Ignore if move host failed.
                pass

            self.virt_utils.update_prop(context, id_,
                                        eon_const.EON_RESOURCE_STATE,
                                        eon_const.EON_RESOURCE_STATE_ACTIVATED)

    def host_commission(self, context, id_, data):
        """Adds the new host to the cluster and provisons
        ovsvapp VM on it.
        :param context
        :id_ id of the cluster
        :param: data
        """
        resource_inventory = self.get_with_inventory(context, id_)
        expected_states = [eon_const.EON_RESOURCE_STATE_ACTIVATED]
        self.validator.validate_state(
            expected_states,
            resource_inventory.get("state"))

        next_state = eon_const.HOST_COMMISSION_MAPPING.get(
            resource_inventory.get("state"))
        self.virt_utils.update_prop(context, id_, eon_const.EON_RESOURCE_STATE,
                                    next_state)
        resource_inventory["state"] = next_state

        eventlet.spawn_n(self._host_commission,
                         context, id_, resource_inventory, data)
        return self.get(context, id_)

    def host_de_commission(self, context, id_, data):
        pass

    def _pre_provisioning_steps(self, context, res_id, data, res_inventory):
        """ updates the state and validates it
        """
        LOG.info("[%s] Executing pre provisioning steps" % res_id)
        expected_state = [eon_const.EON_RESOURCE_STATE_IMPORTED]
        state_in_db = res_inventory.get(eon_const.EON_RESOURCE_STATE)
        # if state not imported raise error
        self.validator.validate_state(expected_state, state_in_db)
        # if resource not baremetal, raise error
        type_in_db = res_inventory.get(eon_const.EON_RESOURCE_TYPE)
        self.validator.validate_type(type_in_db,
                                     eon_const.EON_RESOURCE_TYPE_BAREMETAL)
        next_state = eon_const.RESOURCE_STATE_PROVISON_INITIATED
        self.virt_utils.update_prop(context, res_id,
                                    eon_const.EON_RESOURCE_STATE,
                                    next_state)
        res_inventory["state"] = next_state

        # update the type from baremetal to given resource type
        type_ = data[eon_const.EON_RESOURCE_TYPE]
        self.virt_utils.update_prop(context, res_id, 'type',
                                    type_)
        res_inventory["type"] = data["type"]
        LOG.debug("[%s] pre provisioning comple" % res_id)

    def _provision(self, context, id_, data, resource_inventory):
        """ Execute the provisioning steps in a eventlet thread
        """
        resource_type = data.get(eon_const.EON_RESOURCE_TYPE)
        LOG.info("[%s] Provision started." % id_)
        try:
            resource_id = resource_inventory.get(
                eon_const.EON_RESOURCE_ID)
            resource_password = resource_inventory.get(
                eon_const.EON_RESOURCE_PASSWORD)
            # Update the state to Provisioning post cobbler deploy call
            next_state = eon_const.EON_RESOURCE_STATE_PROVISIONING
            self.virt_utils.update_prop(context, id_,
                                        eon_const.EON_RESOURCE_STATE,
                                        next_state)
            hux_obj = HLMFacadeWrapper(context)
            model = self.virt_utils.create_servers_payload(data,
                                                           resource_inventory)
            # Remove once cobbler deploy role check if resolved
            fake_role_key = eon_const.HLM_PAYLOAD_MAP[eon_const.SERVER_ROLE]
            fake_group_key = eon_const.HLM_PAYLOAD_MAP[eon_const.SERVER_GROUP]
            server_roles = vir_utils.get_hypervisor_roles(hux_obj,
                                                          resource_type)
            server_groups = vir_utils.get_server_groups_with_no_child(hux_obj)
            model[fake_role_key] = server_roles[0]
            model[fake_group_key] = server_groups[0].get("name")
            try:
                hux_obj.get_server_by_id(resource_id)
            except facade_excep.NotFound:
                LOG.info("[%s] Resource not found in input model. "
                         "Creating full spec." % id_)
                hux_obj.create_server(model)
                hux_obj.commit_changes(
                    resource_id, "Provision KVM compute resource")
                hux_obj.config_processor_run()
            hux_obj.cobbler_deploy(resource_id, resource_password)
            hux_obj.cobbler_deploy_status(resource_id)
            LOG.info("[%s] Provision complete" % id_)
            # Update the state to Provisioned
            next_state = eon_const.EON_RESOURCE_STATE_PROVISIONED
            self.virt_utils.update_prop(context, id_,
                                        eon_const.EON_RESOURCE_STATE,
                                        next_state)
        except Exception as e:
            LOG.error("[%s] Provisioning failed. %s " % (id_, e.message))
            self.virt_utils.update_prop(context, id_, 'state',
                                        eon_const.EON_RESOURCE_STATE_IMPORTED)
            self.virt_utils.update_prop(context, id_, 'type',
                                        eon_const.EON_RESOURCE_TYPE_BAREMETAL)
            hux_obj.revert_changes()
            hux_obj.delete_server(resource_id)
            hux_obj.commit_changes(resource_id, "Delete KVM compute resource")
            hux_obj.config_processor_run()
            extra_args = {"extraVars": {
                "nodename": id_
            }}
            LOG.info("Deleting node %s from cobbler db" % str(id_))
            hux_obj.run_playbook('hlm_remove_cobbler_node',
                                 extra_args=extra_args)
            LOG.exception(e)

    def provision(self, context, id_, data):
        """ Provision the new host, adds hypervisor on it.
        :param context
        :id_ id of the resource
        :data properties required for provisioning
        """
        # Get data from db
        resource_inventory = self.get_with_inventory(context, id_)
        # run pre checks and update the state
        self._pre_provisioning_steps(context, id_, data, resource_inventory)
        eventlet.spawn_n(self._provision,
                         context, id_, data,
                         resource_inventory)
        return self.get(context, id_)

    def update_property(self, context, id_, rsrc_id, property_name,
                        property_value):
        return self.db_api.update_property(context, id_, rsrc_id,
                                           property_name, property_value)
