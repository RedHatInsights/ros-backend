import json
import logging
from flask import request
from flask_restful import abort
from ros.lib.models import System, RatingChoicesEnum
from ros.lib.utils import identity, user_data_from_identity

LOG = logging.getLogger(__name__)


def validate_rating_post_api(func):
    """Validate POST rating request."""
    allowed_choices = [c.value for c in RatingChoicesEnum]

    def error_msg(error_code, value):
        errors = {
            400: "is invalid value for rating.",
            422: "is invalid choice of input for rating."
        }
        return (
            f"'{value}' { errors.get(error_code, 'Invalid') }"
            f" Possible values - { *allowed_choices, }"
        )

    def check_for_rating(data):
        rating = None
        try:
            rating = int(data['rating'])
        except ValueError:
            abort(400, message=(error_msg(400, data['rating'])))

        if rating not in allowed_choices:
            abort(422, message=(error_msg(422, data['rating'])))

        return rating

    def check_for_user():
        ident = identity(request)['identity']
        user = user_data_from_identity(ident)
        username = user['username'] if 'username' in user else None

        if username is None:
            abort(403, message="Username doesn't exist")

        return username

    def check_for_system(inventory_id):
        system = System.query.filter(
            System.inventory_id == inventory_id
        ).first()

        if system is None:
            abort(404, message=f"System {inventory_id} doesn't exist.")

        return system.id

    def validate_request(*args, **kwargs):
        username = check_for_user()
        data = None
        try:
            data = json.loads(request.data)
        except json.decoder.JSONDecodeError as err:
            LOG.error('Decoding JSON has failed. %s', repr(err))
            abort(400, message="Decoding JSON has failed.")
        except TypeError as ex:
            LOG.error('Invalid JSON format. %s', repr(ex))
            abort(400, message="Invalid JSON format.")

        inventory_id = data['inventory_id']
        system_id = check_for_system(inventory_id)
        rating = check_for_rating(data)
        new_kwargs = {
            'rating': rating, 'username': username,
            'inventory_id': inventory_id, 'system_id': system_id
        }
        new_kwargs.update(kwargs)
        return func(*args, **new_kwargs)

    return validate_request
