from flask_restful import abort
from sqlalchemy import asc, desc


def sorting_order(order_how):
    """Sorting order method."""
    method_name = None
    if order_how == 'asc':
        method_name = asc
    elif order_how == 'desc':
        method_name = desc
    else:
        abort(
            403,
            message="Incorrect sorting order. Possible values - ASC/DESC"
        )
    return method_name
