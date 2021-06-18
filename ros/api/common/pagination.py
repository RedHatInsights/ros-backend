"""Module to construct response for paginated list."""
from urllib.parse import urlencode
from flask import request

DEFAULT_RECORDS_PER_REP = 10
DEFAULT_OFFSET = 0


def _cast_to_positive_int(integer_string):
    """Cast a string to a positive integer."""
    ret = int(integer_string)
    if ret < 0:
        raise ValueError()
    return ret


def limit_value():
    """Get limit value."""
    limit_param = request.args.get('limit')
    if limit_param:
        try:
            return _cast_to_positive_int(limit_param)
        except ValueError:
            pass
    return DEFAULT_RECORDS_PER_REP


def offset_value():
    """Get offset value."""
    offset_param = request.args.get('offset')
    if offset_param:
        try:
            return _cast_to_positive_int(offset_param)
        except ValueError:
            pass
    return DEFAULT_OFFSET


def _create_link(path, limit, offset, args_dict):
    params = dict(args_dict)
    params["limit"] = limit
    params["offset"] = offset
    return "{}?{}".format(path, urlencode(params))


def _create_first_link(path, limit, _offset, _count, args_dict):
    return _create_link(path, limit, 0, args_dict)


def _create_previous_link(path, limit, offset, _count, args_dict):
    prev_offset = offset - limit
    if offset == 0 or prev_offset < 0:
        return None
    return _create_link(path, limit, prev_offset, args_dict)


def _create_next_link(path, limit, offset, count, args_dict):
    next_offset = limit + offset
    if next_offset >= count:
        return None
    return _create_link(path, limit, next_offset, args_dict)


def _create_last_link(path, limit, _offset, count, args_dict):
    final_offset = count - limit if (count - limit) >= 0 else 0
    return _create_link(path, limit, final_offset, args_dict)


def build_paginated_system_list_response(
        limit, offset, json_list, count, args_dict={}):
    output = {
        "meta": {
            "count": count,
            "limit": limit,
            "offset": offset,
        },
        "links": {
            "first": _create_first_link(
                request.path, limit, offset, count, args_dict
            ),
            "last": _create_last_link(
                request.path, limit, offset, count, args_dict
            ),
            "next": _create_next_link(
                request.path, limit, offset, count, args_dict
            ),
            "previous": _create_previous_link(
                request.path, limit, offset, count, args_dict
            ),
        },
        "data": json_list,
    }
    return output
