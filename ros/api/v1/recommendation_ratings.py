import json
from flask import request
from flask_restful import Resource, abort, fields, marshal_with
from ros.lib.models import RecommendationRating, System, db, RatingChoicesEnum
from ros.lib.utils import identity, user_data_from_identity


class RecommendationRatingsApi(Resource):

    rating_fields = {
        'inventory_id': fields.String,
        'rating': fields.Integer
    }

    @marshal_with(rating_fields)
    def post(self):
        """
            Add or update a rating for a system, by system ID.
            Return the new rating. Any previous rating for this rule by this
            user is amended to the current value.
        """
        ident = identity(request)['identity']
        user = user_data_from_identity(ident)
        username = user['username'] if 'username' in user else None

        if username is None:
            abort(403, message="Username doesn't exist")

        data = json.loads(request.data)
        inventory_id = data['inventory_id']
        allowed_choices = [c.value for c in RatingChoicesEnum]

        def invalid_value_msg(val):
            return (
                f"'{val}' is invalid value for rating."
                f'Possible values - { *allowed_choices, }'
            )
        rating = None
        try:
            rating = int(data['rating'])
        except ValueError:
            abort(400, message=(invalid_value_msg(data['rating'])))

        if rating not in allowed_choices:
            abort(422, message=(invalid_value_msg(data['rating'])))

        system = System.query.filter(
            System.inventory_id == inventory_id
        ).first()

        if system is None:
            abort(404, message=f"System {inventory_id} doesn't exist")

        rating_record = RecommendationRating.query.filter(
            RecommendationRating.system_id == system.id,
            RecommendationRating.rated_by == username).first()

        if rating_record:
            rating_record.rating = rating
            db.session.commit()
            status_code = 200
        else:
            rating_record = RecommendationRating(
                system_id=system.id, rating=rating, rated_by=username
            )
            db.session.add(rating_record)
            db.session.commit()
            status_code = 201

        return {
            'rating': rating_record.rating,
            'inventory_id': inventory_id
        }, status_code
