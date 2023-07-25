from flask_restful import Resource, fields, marshal_with
from ros.lib.models import RecommendationRating, db
from ros.api.common.utils import validate_rating_data
from ros.lib.models import System


class RecommendationRatingsApi(Resource):
    rating_fields = {
        'inventory_id': fields.String,
        'rating': fields.Integer,
        'group_id': fields.String,
    }

    @validate_rating_data
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
        group_id = kwargs.get('group_id', '')
        if group_id:
            sys_query = db.session.query(System.inventory_id). \
                filter((System.inventory_id == inventory_id) &
                       ((System.groups[0]['id'].astext == group_id) | (System.groups == '[]')))
        else:
            sys_query = db.session.query(System.inventory_id). \
                filter((System.inventory_id == inventory_id) & (System.groups == '[]'))

        if sys_query.count() == 0:
            return {}, 401

        rating_record = RecommendationRating.query.filter(
            RecommendationRating.system_id == system_id,
            RecommendationRating.rated_by == username
        ).first()

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
