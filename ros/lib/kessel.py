from typing import Optional
from dataclasses import dataclass
import grpc
from kessel.inventory.v1beta2 import (
    inventory_service_pb2_grpc,
    streamed_list_objects_request_pb2,
    representation_type_pb2,
    subject_reference_pb2,
    resource_reference_pb2,
    reporter_reference_pb2,
    request_pagination_pb2,
    check_request_pb2,
    allowed_pb2
)

from enum import Enum

class Allowed(Enum):
    UNSPECIFIED = 0
    TRUE = 1
    FALSE = 2


@dataclass
class ObjectType:
    resource_type: str
    reporter_type: str

    @staticmethod
    def workspace():
        return ObjectType(
            resource_type="workspace",
            reporter_type="rbac",
        )

    @staticmethod
    def role():
        return ObjectType(
            resource_type="role",
            reporter_type="rbac"
        )


@dataclass
class Resource(ObjectType):
    resource_id: str

    @staticmethod
    def principal(resource_id: str):
        return Resource(
            resource_id=resource_id,
            resource_type="principal",
            reporter_type="rbac",
        )

    @staticmethod
    def role(resource_id: str):
        return Resource(
            resource_id=resource_id,
            resource_type="role",
            reporter_type="rbac",
        )

    @staticmethod
    def workspace(resource_id: str):
        return Resource(
            resource_id=resource_id,
            resource_type="workspace",
            reporter_type="rbac"
        )




class KesselClient:

    def __init__(self, host):
        # It is recommended [1] that both channel and stub are re-used.
        # In python [2], using `ChannelOptions.SingleThreadedUnaryStream` could reduce latency, but the API has been
        # marked experimental for a while.
        # Note: I tried passing options=ChannelOptions.SingleThreadedUnaryStream but it didn't work. The stack trace
        #  showed a cython grpc lib. Also tried options=(ChannelOptions.SingleThreadedUnaryStream) and
        #  options=(ChannelOptions.SingleThreadedUnaryStream,).
        #
        # [1] https://grpc.io/docs/guides/performance/
        # [2] https://grpc.io/docs/guides/performance/#python
        self.channel = grpc.insecure_channel(host)
        self.stub = inventory_service_pb2_grpc.KesselInventoryServiceStub(self.channel)

    def get_resources(self, object_type: ObjectType, relation: str, subject: Resource, limit: Optional[int]=None, fetch_all = True):
        response = self._get_resources_internal(object_type, relation, subject, limit=limit)
        while response is not None:
            continuation_token = None
            for data in response:
                yield data.object
                continuation_token = data.pagination.continuation_token

            response = None
            if fetch_all and continuation_token:
                response = self._get_resources_internal(object_type, relation, subject, limit=limit, continuation_token=continuation_token)


    def _get_resources_internal(self, object_type: ObjectType, relation: str, subject: Resource, limit: Optional[int] = None, continuation_token: Optional[str] = None):
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

    def default_workspace(self, subject: Resource) -> Resource:
        """
        Computes / fetches the default workspace for the subject.
        This is located in kessel.py, but it might be moved elsewhere depending on the actual mechanics of getting the default workspace.
        As of today it only prepends `default-workspace-` which might not be accurate.
        There is an API [1] on RBAC that is able to retrieve the default workspace.

        [1] https://github.com/RedHatInsights/insights-rbac/blob/master/docs/source/specs/v2/openapi.yaml#L30
        :param subject:
        :return:
        """
        return Resource.workspace(f"default-workspace-{subject.resource_id}")


    def default_workspace_check(self, relation: str, subject: Resource) -> Allowed:
        return self.check(self.default_workspace(subject), relation, subject)

    def check(self, resource: Resource, relation: str, subject: Resource) -> Allowed:
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
            return Allowed.TRUE
        elif response.allowed is allowed_pb2.ALLOWED_FALSE:
            return Allowed.FALSE

        return Allowed.UNSPECIFIED
