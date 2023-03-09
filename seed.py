import json
import logging
from ros.lib.models import Rule
from ros.extensions import db
from ros.lib.utils import get_or_create

LOG = logging.getLogger(__name__)


class Seed():

    def run(self):
        self.seed_rule_data()

    def seed_rule_data(self):
        with open("seed.d/rules.json") as f:
            rules = json.loads(f.read())
            for data in rules:
                get_or_create(
                    db.session, Rule, 'rule_id',
                    rule_id=data['rule_id'],
                    description=data['description'],
                    reason=data['reason'],
                    resolution=data['resolution'],
                    condition=data['condition']
                )
                db.session.commit()
        LOG.info("Seeding completed successfully. ROS rules added to database")
