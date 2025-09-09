from dataclasses import dataclass
from enum import Enum


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
            resource_id=f"redhat/{resource_id}",
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
    def workspace(resource_id: str, resource_name: str):
        return Resource(
            resource_id=resource_id,
            resource_type="workspace",
            resource_name=resource_name,
            reporter_type="rbac"
        )


class UserAllowed(Enum):
    UNSPECIFIED = 0
    TRUE = 1
    FALSE = 2
