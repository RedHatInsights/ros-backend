import uuid
import base64
import json
from flask import jsonify, make_response
from flask_restful import abort



def is_valid_uuid(val):
    try:
        uuid.UUID(str(val), version=4)
        return True
    except ValueError:
        return False


def get_or_create(session, model, keys, **kwargs):
    if not keys:
        keys = kwargs.keys()
    if isinstance(keys, str):
        keys = [keys]
    if not isinstance(keys, list):
        raise TypeError('keys argument must be a list or string')
    instance = session.query(model).filter_by(**{k: kwargs[k] for k in keys}).first()
    if instance:
        for k, v in kwargs.items():
            setattr(instance, k, v)
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.flush()
    return instance


def delete_record(session, model, **kwargs):
    """ Deletes a record filtered by key(s) present in kwargs(contains model specific fields)."""
    keys = list(kwargs.keys())
    instance = session.query(model).filter_by(**{k: kwargs[k] for k in keys}).first()
    if instance:
        session.delete(instance)
        session.commit()
    return instance


def identity(request):
    ident = request.headers.get('X-RH-IDENTITY')
    if not ident:
        response = make_response(
            jsonify({"Error": "Authentication token not provided"}), 401)
        abort(response)
    else:
        return json.loads(base64.b64decode(ident))


def user_data_from_identity(identity):
    """
    Get the user details dict from the rh-identity data or error out.
    """
    if 'user' not in identity:
        return None

    return identity['user']


def validate_type(value, type_):
    """
    Validate the type of a value.
    Currently available types: bool
    :param value: Value to validate.
    :param type_: Type to validate against.
    :return: True if the value is of the specified type, False otherwise.
    """
    if type_ == bool:
        # ast.literal_eval does not understand lowercase 'True' or 'False'
        value = value.capitalize() if value in ['true', 'false'] else value
    evaluated_value = type_evaluation.literal_eval(value) if value else None

    return True if type(evaluated_value) == type_ else False


def convert_iops_from_percentage(iops_dict):
    """
    Convert IOPS to MBPS
    :param iops_dict: IOPS dict to convert.
    :return: IOPS values converted to MBPS.
    """
    iops_in_mbps = {}
    for key, value in iops_dict.items():
        iops_in_mbps[key] = float(value) * 100
    return iops_in_mbps


def sort_io_dict(performance_utilization: dict, remove_io_dict: bool = True):
    """
    Sorts io dict by max_io in descending order.
    """
    io_dict = performance_utilization['io']
    io_dict_key = 'io_all' if remove_io_dict is True else 'io'
    del performance_utilization['io']
    sorted_io_dict = {
        io_dict_key: dict(sorted(io_dict.items(), key=lambda x: x[1], reverse=True))
    }
    performance_utilization.update({**sorted_io_dict})
    return performance_utilization
