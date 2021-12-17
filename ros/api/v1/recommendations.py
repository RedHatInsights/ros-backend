from ros.lib.models import Rule, RhAccount, System, db
from ros.lib.utils import is_valid_uuid, identity
from ros.lib.config import INSTANCE_PRICE_UNIT
from flask_restful import Resource, abort, fields, marshal_with
from flask import request


class RecommendationsApi(Resource):

    recommendation_fields = {
        'rule_id':  fields.String,
        'description': fields.String,
        'reason': fields.String,
        'resolution': fields.String,
        'condition': fields.String
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
        if not is_valid_uuid(host_id):
            abort(404, message='Invalid host_id, Id should be in form of UUID4')

        ident = identity(request)['identity']

        filter_description = request.args.get('description')

        account_query = db.session.query(RhAccount.id).filter(RhAccount.account == ident['account_number']).subquery()
        system = db.session.query(System) \
            .filter(System.account_id.in_(account_query)).filter(System.inventory_id == host_id).first()

        if not system:
            abort(404, message="host with id {} doesn't exist"
                  .format(host_id))
        rule_hits = system.rule_hit_details
        recommendations_list = []
        rules_columns = ['rule_id', 'description', 'reason', 'resolution', 'condition']
        if rule_hits:
            for rule_hit in rule_hits:
                if filter_description:
                    rule_data = db.session.query(Rule).filter(Rule.rule_id == rule_hit['rule_id'])\
                                .filter(Rule.description.ilike(f'%{filter_description}%')).first()
                else:
                    rule_data = db.session.query(Rule).filter(Rule.rule_id == rule_hit['rule_id']).first()
                if rule_data:
                    rule_dict = rule_data.__dict__
                    recommendation = {}
                    instance_price = ''
                    summary = ''
                    candidate_string = ''
                    rule_hit_details = rule_hit.get('details')
                    candidates = rule_hit_details.get('candidates')
                    summaries = rule_hit_details.get('summary')
                    instance_price += f'{rule_hit_details.get("price")} {INSTANCE_PRICE_UNIT}'
                    newline = '\n'
                    for skey in rules_columns:
                        if skey == 'reason':
                            formatted_summary = []
                            for msg in summaries:
                                formatted_summary.append(f'\t\u2022 {msg}')
                            summary += newline.join(formatted_summary)
                        elif skey == 'resolution':
                            formatted_candidates = []
                            for candidate in candidates[0:3]:
                                formatted_candidates.append(f'{candidate[0]} ({candidate[1]} {INSTANCE_PRICE_UNIT})')
                            candidate_string += ', '.join(formatted_candidates)
                        recommendation[skey] = eval("f'{}'".format(rule_dict[skey]))
                    recommendations_list.append(recommendation)
        return {
                  'inventory_id': system.inventory_id,
                  'data': recommendations_list,
                  'meta': {'count': len(recommendations_list)}
            }
