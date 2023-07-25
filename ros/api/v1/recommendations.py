from ros.lib.models import Rule, System, db, PerformanceProfile
from ros.lib.utils import is_valid_uuid, identity, system_ids_by_org_id
from ros.api.modules.recommendations import Recommendation
from flask_restful import Resource, abort, fields, marshal_with
from flask import request
from sqlalchemy import exc
from ros.api.common.add_group_filter import include_group_filter


class RecommendationsApi(Resource):
    recommendation_fields = {
        'rule_id': fields.String,
        'description': fields.String,
        'reason': fields.String,
        'resolution': fields.String,
        'condition': fields.String,
        'detected_issues': fields.String,
        'suggested_instances': fields.String,
        'current_instance': fields.String,
        'psi_enabled': fields.Boolean
    }

    meta_fields = {
        'count': fields.Integer
    }

    data_fields = {
        'inventory_id': fields.String,
        'meta': fields.Nested(meta_fields),
        'data': fields.List(fields.Nested(recommendation_fields))
    }

    @marshal_with(data_fields)
    def get(self, host_id):
        system = None
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        ident = identity(request)['identity']

        filter_description = request.args.get('description')
        sys_query = include_group_filter(request, system_ids_by_org_id(ident['org_id'], True))
        system_query = sys_query.filter(System.inventory_id == host_id)
        try:
            system = db.session.execute(system_query).scalar_one()
        except exc.NoResultFound:
            abort(404, message=f"System {host_id} doesn't exist.")

        profile = PerformanceProfile.query.filter_by(system_id=system.id).first()
        if not profile:
            abort(
                404,
                message="No records for host with id {} doesn't exist".format(host_id))

        rule_hits = profile.rule_hit_details
        psi_enabled = profile.psi_enabled
        recommendations_list = []
        if rule_hits:
            for rule_hit in rule_hits:
                if filter_description:
                    rule_data = db.session.scalar(db.select(Rule).filter(Rule.rule_id == rule_hit['rule_id'])
                                                  .filter(Rule.description.ilike(f'%{filter_description}%')))
                else:
                    rule_data = db.session.scalar(db.select(Rule).filter(Rule.rule_id == rule_hit['rule_id']))

                if rule_data:
                    recommendation = Recommendation(
                        rule_data, rule_hit, system, psi_enabled
                    ).__dict__
                    recommendations_list.append(recommendation)
        return {
            'inventory_id': system.inventory_id,
            'data': recommendations_list,
            'meta': {'count': len(recommendations_list)}
        }
