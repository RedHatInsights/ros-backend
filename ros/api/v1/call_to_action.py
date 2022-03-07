from flask_restful import Resource
from flask import request
from ros.lib.utils import (
    identity, system_ids_by_account)
from ros.lib.models import (
    System, PerformanceProfile, db)


class CallToActionApi(Resource):
    def get(self):
        account_number = identity(request)['identity']['account_number']
        system_query = system_ids_by_account(account_number).filter(System.number_of_recommendations > 0)
        query = (
            db.session.query(PerformanceProfile.system_id)
            .filter(PerformanceProfile.system_id.in_(system_query.subquery()))
            .distinct()
        )
        total_system_count = query.count()

        configTryLearn_Object = {
            "try": [{
                "shape": {
                    "title": "Install and begin using Resource optimization service.",
                    "description": "This new service helps manage your public cloud systems.",
                    "link": {
                        "title": "Get started",
                        "href": "/insights/ros?with_suggestions=true",
                    },
                },
            }]
        }
        if total_system_count == 0:
            return {
               "configTryLearn": configTryLearn_Object
            }
        else:
            if total_system_count > 1:
                suffix = 'systems'
            else:
                suffix = 'system'
            return {
                "recommendations": {
                    "redhatInsights": [
                        {
                            "id": "ros-1",
                            "description": "Resource optimization recommends to assess and monitor"
                            + " cloud usage and optimization on these systems",
                            "icon": "cog",
                            "action": {
                                "title": f"View {total_system_count} {suffix}"
                                + " with suggestions",
                                "href": "/insights/ros?with_suggestions=true"
                            }
                        }
                    ]
                },
                "configTryLearn": configTryLearn_Object
            }
