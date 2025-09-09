from typing import Optional
import requests
from urllib.parse import urljoin
from kessel.inventory.v1beta2 import (
    streamed_list_objects_request_pb2,
    representation_type_pb2,
    subject_reference_pb2,
    resource_reference_pb2,
    reporter_reference_pb2,
    request_pagination_pb2,
    check_request_pb2,
    allowed_pb2
)

from ros.lib.kessel.dataclasses_and_enum import ObjectType, Resource, UserAllowed
from ros.lib.kessel.singleton_grpc import get_kessel_stub
from ros.lib.config import (
    get_logger, RBAC_SVC_URL, TLS_CA_PATH,
    KESSEL_OAUTH_CLIENT_ID, KESSEL_OAUTH_CLIENT_SECRET, KESSEL_OAUTH_OIDC_ISSUER
)


LOG = get_logger(__name__)


class KesselClient:

    def __init__(self, host, org_id=None):
        """
        Initialize KesselClient with optional org_id for workspace-based authentication.

        Args:
            host: Kessel service host and port
            org_id: Organization ID for workspace identification
        """
        self.stub = get_kessel_stub(host)
        self.org_id = org_id

    def get_resources(
        self,
        object_type: ObjectType,
        relation: str,
        subject: Resource,
        limit: int = 20,
        fetch_all=True
    ):
        response = self._get_resources_internal(object_type, relation, subject, limit=limit)
        while response is not None:
            continuation_token = None
            for data in response:
                yield data.object
                continuation_token = data.pagination.continuation_token

            response = None
            if fetch_all and continuation_token:
                response = self._get_resources_internal(object_type,
                                                        relation,
                                                        subject,
                                                        limit=limit,
                                                        continuation_token=continuation_token)

    def _get_resources_internal(self,
                                object_type: ObjectType,
                                relation: str,
                                subject: Resource,
                                limit: int,
                                continuation_token: Optional[str] = None):
        request = streamed_list_objects_request_pb2.StreamedListObjectsRequest(
            object_type=representation_type_pb2.RepresentationType(
                resource_type=object_type.resource_type,
                reporter_type=object_type.reporter_type,
            ),
            relation=relation,
            subject=subject_reference_pb2.SubjectReference(
                resource=resource_reference_pb2.ResourceReference(
                    resource_type=subject.resource_type,
                    resource_id=subject.resource_id,
                    reporter=reporter_reference_pb2.ReporterReference(
                        type=subject.reporter_type
                    ),
                ),
            ),
            pagination=request_pagination_pb2.RequestPagination(
                limit=limit,
                continuation_token=continuation_token
            )
        )

        return self.stub.StreamedListObjects(request)

    def _get_auth_credentials(self):
        """
        Helper method to create OAuth2ClientCredentials for RBAC API authentication.
        Following the kessel-sdk-py auth_insecure.py pattern with OIDC discovery.

        :return: OAuth2ClientCredentials object or None if configuration is missing
        """
        try:
            # Check if OAuth configuration is available
            if not KESSEL_OAUTH_CLIENT_ID or not KESSEL_OAUTH_CLIENT_SECRET or not KESSEL_OAUTH_OIDC_ISSUER:
                LOG.warning("OAuth2 configuration missing - cannot create auth_credentials")
                return None

            # Import kessel auth components only when needed
            try:
                from kessel.authn import OAuth2ClientCredentials, fetch_oidc_discovery
            except ImportError:
                LOG.error("kessel.authn not available - cannot create OAuth2ClientCredentials")
                return None

            # Fetch OIDC discovery information to get token endpoint
            try:
                LOG.info(f"Fetching OIDC discovery from: {KESSEL_OAUTH_OIDC_ISSUER}")
                discovery = fetch_oidc_discovery(KESSEL_OAUTH_OIDC_ISSUER)
                token_endpoint = discovery.token_endpoint

                if not token_endpoint:
                    LOG.error("No token_endpoint found in OIDC discovery response")
                    return None

                LOG.info(f"Discovered token endpoint: {token_endpoint}")

            except Exception as discovery_err:
                LOG.error(f"Failed to fetch OIDC discovery: {discovery_err}")
                return None

            # Create OAuth2ClientCredentials with discovered token endpoint
            auth_credentials = OAuth2ClientCredentials(
                client_id=KESSEL_OAUTH_CLIENT_ID,
                client_secret=KESSEL_OAUTH_CLIENT_SECRET,
                token_endpoint=token_endpoint,
            )

            LOG.info("OAuth2ClientCredentials created successfully for RBAC API using OIDC discovery")
            return auth_credentials

        except Exception as err:
            LOG.error(f"Error creating OAuth2ClientCredentials: {err}")
            return None

    def default_workspace(self):
        """
        Fetches the default workspace with name and ID using RBAC API.
        Uses the RBAC v2 workspaces endpoint with type=default filter.
        Since there is only one default workspace per organization, this method returns
        a single workspace dictionary or None.

        Uses OIDC discovery and OAuth2ClientCredentials to authenticate with RBAC API.

        :return: Dict with workspace name and id, or None if no workspace found
        """
        try:
            # Get OAuth2ClientCredentials using helper method
            auth_credentials = self._get_auth_credentials()
            if not auth_credentials:
                LOG.error("No OAuth2ClientCredentials available for RBAC API call")
                return None

            # Build the RBAC workspaces URL with type=default filter
            rbac_workspaces_url = urljoin(RBAC_SVC_URL, "/api/rbac/v2/workspaces/?type=default")

            LOG.info(f"Fetching default workspace from RBAC API: {rbac_workspaces_url}")

            # Get access token from OAuth2ClientCredentials
            try:
                access_token = auth_credentials.get_token()
                auth_header = {"authorization": f"Bearer {access_token}"}
            except Exception as token_err:
                LOG.error(f"Failed to get access token from OAuth2ClientCredentials: {token_err}")
                return None

            # Make the HTTP request to RBAC API with OAuth2 authentication
            response = requests.get(
                rbac_workspaces_url,
                headers=auth_header,
                verify=TLS_CA_PATH,
                timeout=30
            )

            # Check if request was successful
            if response.status_code == requests.codes.ok:
                rbac_data = response.json()

                # Parse the RBAC response to extract workspace details
                workspaces = rbac_data.get('data', [])

                if workspaces:
                    # Get the default workspace (should be only one)
                    default_workspace = workspaces[0]

                    workspace_name = default_workspace.get('name', 'Default Workspace')
                    workspace_id = default_workspace.get('id', '')

                    LOG.info(f"Found default workspace: {workspace_name} (ID: {workspace_id})")
                    return Resource.workspace(workspace_id, workspace_name)
                else:
                    LOG.warning("No default workspace found in RBAC API response")
                    return None

            else:
                LOG.error(f"RBAC API request failed with status {response.status_code}: {response.text}")
                return None

        except requests.exceptions.Timeout:
            LOG.error("Timeout while calling RBAC API for default workspace")
            return None
        except requests.exceptions.RequestException as err:
            LOG.error(f"Request error while calling RBAC API: {err}")
            return None
        except Exception as err:
            LOG.error(f"Unexpected error fetching default workspace from RBAC API: {err}")
            return None

    def default_workspace_check(self, relation: str, subject: Resource) -> UserAllowed:
        return self.check(self.default_workspace(self))

    def check(self, resource: Resource, relation: str, subject: Resource) -> UserAllowed:
        request = check_request_pb2.CheckRequest(
            subject=subject_reference_pb2.SubjectReference(
                resource=resource_reference_pb2.ResourceReference(
                    resource_id=subject.resource_id,
                    resource_type=subject.resource_type,
                    reporter=reporter_reference_pb2.ReporterReference(
                        type=subject.reporter_type
                    )
                )
            ),
            relation=relation,
            object=resource_reference_pb2.ResourceReference(
                resource_id=resource.resource_id,
                resource_type=resource.resource_type,
                reporter=reporter_reference_pb2.ReporterReference(
                    type=resource.reporter_type
                )
            ),
        )

        response = self.stub.Check(request)
        if response.allowed is allowed_pb2.ALLOWED_TRUE:
            return UserAllowed.TRUE
        elif response.allowed is allowed_pb2.ALLOWED_FALSE:
            return UserAllowed.FALSE

        return UserAllowed.UNSPECIFIED
