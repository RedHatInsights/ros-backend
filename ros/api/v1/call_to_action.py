from flask_restful import Resource
from flask import request
from ros.lib.utils import (
    org_id_from_identity_header, system_ids_by_org_id)
from ros.lib.models import (
    PerformanceProfile, db)


class CallToActionApi(Resource):
    def get(self):
        org_id = org_id_from_identity_header(request)
        system_query = system_ids_by_org_id(org_id).filter(PerformanceProfile.number_of_recommendations > 0)
        query = (
            db.session.query(PerformanceProfile.system_id)
            .filter(PerformanceProfile.system_id.in_(system_query.subquery()))
        )
        total_system_count = query.count()

        configTryLearn_Object = {
            "try": [{
                "shape": {
                    "title": "Install and begin using Resource optimization service.",
                    "description": "Optimize your spending in public cloud.",
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
