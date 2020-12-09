import uuid


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val), version=4)
        return True
    except ValueError:
        return False
