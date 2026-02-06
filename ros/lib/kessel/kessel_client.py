from typing import Optional
from kessel.inventory.v1beta2 import (
    streamed_list_objects_request_pb2,
    representation_type_pb2,
    subject_reference_pb2,
    resource_reference_pb2,
    reporter_reference_pb2,
    request_pagination_pb2,
)

from ros.lib.kessel.dataclasses_and_enum import ObjectType, Resource
from ros.lib.kessel.kessel_shared import get_kessel_stub
from ros.lib.config import get_logger


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
        limit: int = 1000,
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
