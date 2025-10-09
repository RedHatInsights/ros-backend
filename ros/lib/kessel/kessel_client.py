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
from ros.lib.kessel.kessel_shared import get_kessel_stub, get_cached_kessel_auth_credentials
from ros.lib.config import (
    get_logger, RBAC_SVC_URL, TLS_CA_PATH
)
from ros.extensions import cache


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

    def default_workspace(self):
        """
        Fetches the default workspace with name and ID using RBAC API.
        Uses Redis caching to avoid repeated API calls for the same organization.
        Uses the RBAC v2 workspaces endpoint with type=default filter.
        Since there is only one default workspace per organization, this method returns
        a single workspace dictionary or None.

        Uses OIDC discovery and OAuth2ClientCredentials to authenticate with RBAC API.
        Includes x-rh-rbac-org-id header as required by RBAC middleware.

        :return: Dict with workspace name and id, or None if no workspace found
        """
        try:
            if not self.org_id:
                LOG.error("org_id is required for RBAC API call but not provided")
                return None

            # Check cache first
            cache_key = f"default_workspace_{self.org_id}"
            cached_workspace = cache.get(cache_key)
            if cached_workspace:
                LOG.info(f"Using cached default workspace for org_id: {self.org_id}")
                # Cached data should contain workspace_id and workspace_name
                return Resource.workspace(cached_workspace['workspace_id'], cached_workspace['workspace_name'])

            auth_credentials = get_cached_kessel_auth_credentials()
            if not auth_credentials:
                LOG.error("No OAuth2ClientCredentials available for RBAC API call")
                return None

            rbac_workspaces_url = urljoin(RBAC_SVC_URL, "/api/rbac/v2/workspaces/?type=default")

            LOG.info(f"Fetching default workspace from RBAC API: {rbac_workspaces_url}")

            try:
                token_result = auth_credentials.get_token()
                access_token = token_result[0]
                headers = {
                    "authorization": f"Bearer {access_token}",
                    "x-rh-rbac-org-id": str(self.org_id)
                }
            except Exception as token_err:
                LOG.error(f"Failed to get access token from OAuth2ClientCredentials: {token_err}")
                return None

            response = requests.get(
                rbac_workspaces_url,
                headers=headers,
                verify=TLS_CA_PATH,
                timeout=30
            )

            if response.status_code == requests.codes.ok:
                rbac_data = response.json()

                workspaces = rbac_data.get('data', [])

                if workspaces:

                    default_ws = workspaces[0]

                    workspace_name = default_ws.get('name', 'Default Workspace')
                    workspace_id = default_ws.get('id', '')

                    # Cache the workspace details for future use
                    # Use a longer TTL since default workspace details rarely change
                    workspace_cache_data = {
                        'workspace_id': workspace_id,
                        'workspace_name': workspace_name
                    }
                    cache.set(cache_key, workspace_cache_data, timeout=14400)  # 4 hours TTL

                    LOG.info(f"Found and cached default workspace: {workspace_name} (ID: {workspace_id})")
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
        return self.check(self.default_workspace(), relation, subject)

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
