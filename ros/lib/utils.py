import uuid
import base64
import json

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val), version=4)
        return True
    except ValueError:
        return False


def identity(request):
    ident = request.headers.get('X-RH-IDENTITY')
    return json.loads(base64.b64decode(ident))
