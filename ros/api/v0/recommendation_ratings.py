import json
from flask import request
from flask_restful import Resource, abort
from ros.lib.models import RecommendationRating, System, db

from ros.lib.utils import identity, user_data_from_identity
from ros.lib.app import app


class RecommendationRatingsApi(Resource):
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
        rating = data['rating']
        system = System.query.filter(
            System.inventory_id == inventory_id
        ).first()

        if system is None:
            abort(404, message="System {} doesn't exist"
                  .format(inventory_id))

        rating_record = RecommendationRating.query.filter(
            RecommendationRating.system_id == system.id,
            RecommendationRating.rated_by == username).first()
        if rating_record:
            rating_record.rating = rating
        else:
            rating_record = RecommendationRating(
                system_id=system.id, rating=rating, rated_by=username
            )
            db.session.add(rating_record)

        # FIXUP - handle validation
        db.session.commit()
