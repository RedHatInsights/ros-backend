from ros.lib.models import Rule, RhAccount, System, db
from ros.lib.utils import is_valid_uuid, identity
from flask_restful import Resource, abort, fields, marshal_with
from flask import request


class RecommendationApi(Resource):

    recommendation_fields = {
        'rule_id':  fields.String,
        'description': fields.String,
        'reason': fields.String,
        'resolution': fields.String,
        'condition': fields.String
    }
    data_fields = {
        'host_id': fields.String,
        'recommendation_count': fields.Integer,
        'recommendations': fields.List(fields.Nested(recommendation_fields))
    }

    @marshal_with(data_fields)
    def get(self, host_id):
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        ident = identity(request)['identity']

        account_query = db.session.query(RhAccount.id).filter(RhAccount.account == ident['account_number']).subquery()
        system_query = db.session.query(System) \
            .filter(System.account_id.in_(account_query)).filter(System.inventory_id == host_id).first()

        if not system_query:
            abort(404, message="host with id {} doesn't exist"
                  .format(host_id))
        rule_hits = system_query.rule_hit_details
        recommendations = []
        rules_columns = ['rule_id', 'description', 'reason', 'resolution', 'condition']
        if rule_hits:
            for rule_hit in rule_hits:
                rule_data = db.session.query(Rule).filter(Rule.rule_id == rule_hit['rule_id']).first()
                if rule_data:
                    rule_dict = rule_data.__dict__
                    recommendation = {}
                    for skey in rules_columns:
                        recommendation[skey] = eval("f'{}'".format(rule_dict[skey]))
                    recommendations.append(recommendation)

            record = {}
            record['host_id'] = system_query.inventory_id
            record['recommendation_count'] = len(system_query.rule_hit_details)
            record['recommendations'] = recommendations
            return record
        else:
            abort(404, message="host with id {} doesn't have any recommendation"
                  .format(host_id))
