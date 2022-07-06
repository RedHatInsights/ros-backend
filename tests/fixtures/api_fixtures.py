import json
from base64 import b64encode

import pytest


@pytest.fixture(scope="session")
def auth_token():
    identity = {
        "identity": {
            "account_number": "12345",
            "type": "User",
            "user": {
                "username": "tuser@redhat.com",
                "email": "tuser@redhat.com",
                "first_name": "test",
                "last_name": "user",
                "is_active": True,
                "is_org_admin": False,
                "is_internal": True,
                "locale": "en_US"
            },
            "org_id": "000001",
            "internal": {
                "org_id": "000001"
            }
        }
    }
    auth_token = b64encode(json.dumps(identity).encode('utf-8'))
    return auth_token
