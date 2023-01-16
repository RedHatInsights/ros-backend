import json
from flask import request
from flask_restful import Resource, abort, fields, marshal_with
from ros.lib.models import RecommendationRating, System, db, RatingChoicesEnum
from ros.lib.utils import identity, user_data_from_identity


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
            f"Possible values - { *allowed_choices, }"
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
            abort(404, message=f"System {inventory_id} doesn't exist")

        return system.id

    def validate_request(*args, **kwargs):
        username = check_for_user()
        data = json.loads(request.data)
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


class RecommendationRatingsApi(Resource):

    rating_fields = {
        'inventory_id': fields.String,
        'rating': fields.Integer
    }

    @validate_rating_post_api
    @marshal_with(rating_fields)
    def post(self, **kwargs):
        """
            Add or update a rating for a system, by system ID.
            Return the new rating. Any previous rating for this rule by this
            user is amended to the current value.
        """
        username = kwargs.get('username')
        inventory_id = kwargs.get('inventory_id')
        rating = kwargs.get('rating')
        system_id = kwargs.get('system_id')

        rating_record = RecommendationRating.query.filter(
            RecommendationRating.system_id == system_id,
            RecommendationRating.rated_by == username).first()

        if rating_record:
            rating_record.rating = rating
            db.session.commit()
            status_code = 200
        else:
            rating_record = RecommendationRating(
                system_id=system_id, rating=rating, rated_by=username
            )
            db.session.add(rating_record)
            db.session.commit()
            status_code = 201

        return {
            'rating': rating_record.rating,
            'inventory_id': inventory_id
        }, status_code
