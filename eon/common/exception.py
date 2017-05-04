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

_FATAL_EXCEPTION_FORMAT_ERRORS = False


class EonException(Exception):
    """
    Base eon Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred")

    def __init__(self, message=None, **kwargs):
        if not message:
            message = self.message
        try:
            message = message % kwargs
        except Exception as e:
            if _FATAL_EXCEPTION_FORMAT_ERRORS:
                raise e
            else:
                # at least get the core message out if something happened
                pass
        self.message = message
        super(EonException, self).__init__(message)


class UserException(Exception):
    def __init__(self, reason=None, resolution=None):
        self.message = reason
        self.resolution = resolution
        super(UserException, self).__init__()


class GetException(EonException):
    message = _("%(msg)s")


class UpdateException(EonException):
    message = _("%(msg)s")


class CreateException(EonException):
    message = _("%(msg)s")


class MissingArgumentError(EonException):
    message = _("Missing required argument.")


class MissingCredentialError(EonException):
    message = _("Missing required credential: %(required)s")


class BadAuthStrategy(EonException):
    message = _("Incorrect auth strategy, expected \"%(expected)s\" but "
                "received \"%(received)s\"")


class NotFound(EonException):
    message = _("An object with the specified identifier was not found.")


class UnknownScheme(EonException):
    message = _("Unknown scheme '%(scheme)s' found in URI")


class BadStoreUri(EonException):
    message = _("The Store URI was malformed.")


class Duplicate(EonException):
    message = _("An object with the same identifier already exists.")


class InvalidUUIDInURI(EonException):
    message = _("Invalid UUID '%(uuid)s'")


class AuthBadRequest(EonException):
    message = _("Connect error/bad request to Auth service at URL %(url)s.")


class AuthUrlNotFound(EonException):
    message = _("Auth service at URL %(url)s not found.")


class AuthorizationFailure(EonException):
    message = _("Authorization failed.")


class NotAuthenticated(EonException):
    message = _("You are not authenticated.")


class Forbidden(EonException):
    message = _("You are not authorized to complete this action.")


class UploadOVAFailure(EonException):
    message = _("Observed failures when uploading OVA: %(error)s")


# NOTE(bcwaldon): here for backwards-compatability, need to deprecate.
class NotAuthorized(Forbidden):
    message = _("You are not authorized to complete this action.")


class Invalid(EonException):
    message = _("Data supplied was not valid.")


class InvalidSortKey(Invalid):
    message = _("Sort key supplied was not valid.")


class InvalidFilterRangeValue(Invalid):
    message = _("Unable to filter using the specified range.")


class ReadonlyProperty(Forbidden):
    message = _("Attribute '%(property)s' is read-only.")


class ReservedProperty(Forbidden):
    message = _("Attribute '%(property)s' is reserved.")


class AuthorizationRedirect(EonException):
    message = _("Redirecting to %(uri)s for authorization.")


class DatabaseMigrationError(EonException):
    message = _("There was an error migrating the database.")


class ClientConnectionError(EonException):
    message = _("There was an error connecting to a server")


class ClientConfigurationError(EonException):
    message = _("There was an error configuring the client.")


class MultipleChoices(EonException):
    message = _("The request returned a 302 Multiple Choices. This generally "
                "means that you have not included a version indicator in a "
                "request URI.\n\nThe body of response returned:\n%(body)s")


class LimitExceeded(EonException):
    message = _("The request returned a 413 Request Entity Too Large. This "
                "generally means that rate limiting or a quota threshold was "
                "breached.\n\nThe response body:\n%(body)s")

    def __init__(self, *args, **kwargs):
        self.retry_after = (int(kwargs['retry']) if kwargs.get('retry')
                            else None)
        super(LimitExceeded, self).__init__(*args, **kwargs)


class ServiceUnavailable(EonException):
    message = _("The request returned 503 Service Unavailable. This "
                "generally occurs on service overload or other transient "
                "outage.")

    def __init__(self, *args, **kwargs):
        self.retry_after = (int(kwargs['retry']) if kwargs.get('retry')
                            else None)
        super(ServiceUnavailable, self).__init__(*args, **kwargs)


class ServerError(EonException):
    message = _("The request returned 500 Internal Server Error.")


class UnexpectedStatus(EonException):
    message = _("The request returned an unexpected status: %(status)s."
                "\n\nThe response body:\n%(body)s")


class InvalidContentType(EonException):
    message = _("Invalid content type %(content_type)s")


class BadRegistryConnectionConfiguration(EonException):
    message = _("Registry was not configured correctly on API server. "
                "Reason: %(reason)s")


class BadStoreConfiguration(EonException):
    message = _("Store %(store_name)s could not be configured correctly. "
                "Reason: %(reason)s")


class BadDriverConfiguration(EonException):
    message = _("Driver %(driver_name)s could not be configured correctly. "
                "Reason: %(reason)s")


class MaxRedirectsExceeded(EonException):
    message = _("Maximum redirects (%(redirects)s) was exceeded.")


class CertsGenerationFailed(EonException):
    message = _("Error in generating the required certs for compute")


class InvalidRedirect(EonException):
    message = _("Received invalid HTTP redirect.")


class NoServiceEndpoint(EonException):
    message = _("Response from Keystone does not contain a endpoint.")


class WorkerCreationFailure(EonException):
    message = _("Server worker creation failed: %(reason)s.")


class SchemaLoadError(EonException):
    message = _("Unable to load schema: %(reason)s")


class InvalidObject(EonException):
    message = _("Provided object does not match schema "
                "'%(schema)s': %(reason)s")


class UnsupportedHeaderFeature(EonException):
    message = _("Provided header feature is unsupported: %(feature)s")


class RPCError(EonException):
    message = _("%(cls)s exception was raised in the last rpc call: %(val)s")


class ValidTemplateNotFound(EonException):
    message = _("Template '%(template)s' is not found.")


class NovaComputeTimeout(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class ClusterDeactivationFailure(EonException):
    message = _("The cluster could not be deactivated"
                " as a compute resource : %(reason)s")


class ClusterActivationFailure(EonException):
    message = _("The cluster activation Failed : %(reason)s")


class VCenterRegisterFailure(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class VCenterUpdateFailure(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class VCenterUnregisterFailure(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class VcenterAuthFailure(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class AddressResolutionFailure(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class InternalFailure(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class ResourceExists(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class ResourceNotFound(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class VcenterConfigException(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class InvalidOperation(Invalid):
    message = _("Invalid Operation")


class ProxyIPNotAvailableError(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class ProxyUpgradeFailure(EonException):
    message = _("Failed to upgrade Proxy.")


class InvalidClusterConfiguration(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class UnexpectedDBException(EonException):
    message = _("Database error has occurred [%(reason)s].")


class ProxyVmError(EonException):
    message = _("Proxy VM has errors: %(reason)s")


class ClusterNotImported(EonException):
    message = _("cluster %(cluster_id)s is not imported")


class ClusterUnImportFailure(EonException):
    message = _("Failed to unimport cluster %(cluster_id)s")


class ClusterImportFailure(EonException):
    message = _("Failed to import cluster %(cluster_name)s")


class InvalidRequest(EonException):
    message = _("Invalid api request")


class NoSharedDataStoreFound(EonException):
    message = _("cluster %(cluster_name)s does not have Shared datastore")


class NoHostFound(EonException):
    message = _("cluster %(cluster_name)s does not have any host")


class SetNetworkInfoFailure(EonException):
    message = _("Failed to set network properties")


class DeleteNetworkInfoFailure(EonException):
    message = _("Failed to delete network properties")


class InvalidCIDRException(EonException):
    message = _("Invalid CIDR has been provided")


class InsufficientIPException(EonException):
    message = _("Insufficient IPs to continue the installation")


class DriverException(EonException):
    message = _("An exception occurred during Proxy/Network driver"
                " node operation")


class HostCommissioningException(EonException):
    message = _("An exception occurred during host commissioning operation")


class VcenterConnectionException(DriverException):
    message = _("An exception occurred while connecting to the vCenter Server")


class DatacenterNotfoundError(DriverException):
    message = _("Couldn't find the Datacenter")


class ClusterNotfoundError(DriverException):
    message = _("Couldn't find the Cluster")


class PCIDeviceNotfoundError(DriverException):
    message = _("Couldn't find the PCI device")


class TemplateNotfoundError(DriverException):
    message = _("Couldn't find the hlm-shell-vm template to create VMs")


class VMwareToolsNotRunning(DriverException):
    message = _("Either the VMware tools service is not running/not installed"
                " or it is out of date.")


class CustomizationError(DriverException):
    message = _("Failed to customize the service VM")


class ProxyException(DriverException):
    message = _("An exception occurred during Proxy node operation")


class NetworkDriverException(DriverException):
    message = _("An exception occurred during network driver node operation")


class RetrieveException(EonException):
    message = _("Error retrieving. Reason: %(msg)s")


class OVSvAppException(NetworkDriverException):
    message = _("An exception occurred during OVSvApp node operation")


class OVSvAppValidationError(NetworkDriverException):
    message = _("OVSvApp installation failed due to %(reason)s")


class NetworkPropertyNotFound(DriverException):
    message = _("Network properties not set in the database")


class ProxyTemplateNotFound(ProxyException):
    message = _("Proxy template %(template_name)s not found in the vCenter")


class ProxyNotFound(ProxyException):
    message = _("Proxy VM %(vm_name)s not found in the vCenter")


class ProxyCloneFailure(ProxyException):
    message = _("Proxy VM %(vm_name)s failed to clone due to %(reason)s")


class ProxyReconfigureFailure(ProxyException):
    message = _("Proxy VM %(vm_name)s failed to reconfigure due to %(reason)s")


class ProxyNoHostFound(ProxyException):
    message = _("No Host found in cluster %(cluster_name)s to deploy Proxy VM")


class ProxyNoValidDatastoreFound(ProxyException):
    message = _("No Valid Datastore found in cluster %(cluster_name)s to "
                "deploy Proxy VM")


class ProxyNetworkAttachFailure(ProxyException):
    message = _("Proxy VM %(vm_name)s failed to attach network"
                " due to %(reason)s")


class ProxyPowerOnFailure(ProxyException):
    message = _("Proxy VM %(vm_name)s failed to Power On due to %(reason)s")


class ProxyPowerOffFailure(ProxyException):
    message = _("Proxy VM %(vm_name)s failed to Power Off due to %(reason)s")


class ProxyDeleteFailure(ProxyException):
    message = _("Proxy VM %(vm_name)s failed to delete due to %(reason)s")


class DriverUnavailableError(EonException):
    message = _("No valid driver available for type : '%(type_)s'")


class InsufficientParamsError(EonException):
    message = _("%(msg)s")


class InvalidBoolError(EonException):
    message = _("Invalid boolean: %(bool_)s, reason: %(err)s")


class InvalidIdError(EonException):
    message = _("Invalid ID: %(err)s")


class InvalidNameError(EonException):
    message = _("Invalid name: %(err)s")


class InvalidUsernameError(EonException):
    message = _("Invalid username: %(err)s")


class InvalidPasswordError(EonException):
    message = _("Invalid password: %(err)s")


class InvalidIPAddressError(EonException):
    message = _("Invalid IP address: %(err)s")


class InvalidPortError(EonException):
    message = _("Invalid port: %(err)s")


class InvalidStringError(EonException):
    message = _("Invalid String: '%(string)s', reason: %(err)s")


class InvalidStateError(EonException):
    message = _("Invalid state '%(observed)s' observed. "
        "expected : %(expected)s")


class PreActivationCheckError(EonException):
    message = _("Pre-activation check failed, Reason: %(err)s")


class WarningException(UserException):
    def __init__(self, reason=None, resolution=None):
        UserException.__init__(self, reason=reason, resolution=resolution)


class ActivationFailure(EonException):
    message = _("Failed to activate resource %(resource_name)s, "
                "Reason: %(err)s")


class NetworkPropertiesJSONError(EonException):
    message = _("Failed to populate network properties JSON for "
                "%(resource_type)s, Reason: %(err)s")


class DeactivationFailure(EonException):
    message = _("Failed to deactivate resource %(resource_name)s, "
                "Reason: %(err)s")


class DeleteException(EonException):
    message = _("Delete failed, Reason: %(err)s")


class EonAgentException(EonException):
    message = _("%(msg)s")


class UnsupportedVCenterVersion(EonException):
    message = _("VCenter add failed, Reason: %(err)s")


class HostnameException(EonException):
    message = _("Failed to get host name for resource %(resource_name)s, "
                "Reason: %(err)s")


class NovaHypervisorNotFoundException(EonException):
    message = _("Post-activation check for resource %(resource_name)s failed, "
                "Reason: %(err)s")


class NeutronAgentNotFoundException(EonException):
    message = _("Post-activation check for resource %(resource_name)s failed, "
                "Reason: %(err)s")


class OVSvAPPNotUpException(EonException):
    message = _("Post-activation check for resource %(resource_name)s failed, "
                "Reason: OVSvAPP agents are not up")


class HyperVPSScriptError(EonException):
    message = _("Error in executing PS script on Hyper-V host: %(err)s")


class PyWinRMAuthenticationError(EonException):
    message = _("Invalid credentials given")


class PyWinRMConnectivityError(EonException):
    message = _("WinRM configuration or network error: %(err)s")


class HyperVHostUnSupportedOSError(EonException):
    # TODO: Add additional OS as needed.
    message = _("Supported OS for 'Hyper-V' are 'WIN 2012 R2'")


class HyperVHostUnSupportedOSEditionError(EonException):
    # TODO: Add additional OS as needed.
    message = _("Supported OS editions are Datacenter Server Edition,"
                "Enterprise Server Edition, Datacenter Server Core Edition,"
                "Enterprise Server Core Edition, Hyper-V Server")


class HyperVHostVirtualizationNotEnabledError(EonException):
    message = _("'Hyper-V' role not enabled in the host")


class HyperVPyWinRMExectionError(EonException):
    message = _("Failed to execute powershell script through 'pywinrm' in "
                "'Hyper-V host'")


class HyperVHostConnectivityError(EonException):
    message = _("Failed while connecting to 'Hyper-V host'")


class HyperVHostAuthenticationError(EonException):
    message = _("Invalid credentials given")


class RhelCommandNoneZeroException(EonException):
    message = _("Command returned non zero status: %(err)s")


class AuthenticationError(EonException):
    message = _("An authentication error occurred : %(err)s")


class UnsupportedDeployment(EonException):
    message = _("An Unsupported model for the "
                "hypervisor has been deployed : %(msg)s")
