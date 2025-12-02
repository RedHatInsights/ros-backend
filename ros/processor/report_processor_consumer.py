import json
from datetime import datetime, timezone
from prometheus_client import start_http_server

from ros.lib import consume
from ros.lib.app import app
from ros.extensions import db
from ros.lib.models import RhAccount, System
from ros.lib.config import (
    ROS_EVENTS_TOPIC,
    METRICS_PORT,
    get_logger,
    GROUP_ID_REPORT_PROCESSOR,
)
from ros.lib.utils import (
    get_or_create,
    insert_performance_profiles,
    update_system_record
)

logging = get_logger(__name__)


class ReportProcessorConsumer:
    def __init__(self):
        self.consumer = consume.init_consumer(ROS_EVENTS_TOPIC, GROUP_ID_REPORT_PROCESSOR)
        self.service = 'REPORT_PROCESSOR'

    def run(self):
        logging.info(f"{self.service} - ReportProcessor is running. Awaiting msgs.")

        try:
            while True:
                message = self.consumer.poll(timeout=1.0)
                if message is None:
                    continue

                try:
                    self.process_message(message)
                except json.JSONDecodeError as error:
                    logging.error(f"{self.service} - Failed to decode message: {error}")
                except Exception as error:
                    logging.error(f"{self.service} - Error processing message: {error}")

        except Exception as error:
            logging.error(f"{self.service} - error: {error}")
        finally:
            self.consumer.close()

    def process_message(self, message):
        payload = json.loads(message.value().decode('utf-8'))

        with app.app_context():
            has_performance_data = self._has_performance_data(payload)

            if has_performance_data:
                self._process_with_performance_data(payload)
            else:
                self._process_without_performance_data(payload)

            self.consumer.commit()

    def _has_performance_data(self, payload):
        return (
            'performance_record' in payload or
            'performance_utilization' in payload or
            'rule_hit_details' in payload
        )

    def _build_system_fields(self, payload, account_id=None):
        inventory_id = payload.get('id')
        system_fields = {
            "inventory_id": inventory_id,
            "display_name": payload.get('display_name'),
            "fqdn": payload.get('fqdn'),
            "stale_timestamp": payload.get('stale_timestamp'),
            "groups": payload.get('groups', []),
            "operating_system": payload.get('operating_system'),
            "cloud_provider": payload.get('cloud_provider')
        }

        if account_id is not None:
            system_fields["tenant_id"] = account_id

        return system_fields

    def _process_without_performance_data(self, payload):
        """
        Process API events or create/update events without PCP data.

        Handles:
        - is_ros_v2 = True & is_pcp_raw_data_collected = False
        - Via API updates

        This method should:
        1. Create/Get RhAccount using org_id
        2. Create or Update System record
        """
        event_type = payload.get('type')
        org_id = payload.get('org_id')
        inventory_id = payload.get('id')

        logging.debug(f"{self.service} - Processing {event_type} event for system {inventory_id}")

        if event_type == 'updated':
            system_fields = self._build_system_fields(payload)
            system = update_system_record(db.session, **system_fields)

            if system is not None:
                db.session.commit()
                logging.info(
                    f"{self.service} - Updated system {system.inventory_id} ({system.id})"
                )
            else:
                logging.warning(
                    f"{self.service} - System {inventory_id} not found for update."
                )

        elif event_type == 'created':
            account = get_or_create(
                db.session, RhAccount, 'org_id',
                org_id=org_id
            )

            system_fields = self._build_system_fields(payload, account.id)
            system = get_or_create(db.session, System, 'inventory_id', **system_fields)

            db.session.commit()
            logging.info(
                f"{self.service} - Created system {system.inventory_id} ({system.id})"
            )

    def _process_with_performance_data(self, payload):
        """
        Process create/update events with PCP data.

        Handles:
        - is_ros_v2 = True & is_pcp_raw_data_collected = True

        This method should:
        1. Create/Get RhAccount using org_id
        2. Create or Update System record (including ROS rules data)
        3. Create/Update PerformanceProfile and PerformanceProfileHistory
        """
        org_id = payload.get('org_id')
        inventory_id = payload.get('id')

        logging.debug(f"{self.service} - Processing event with performance data for system {inventory_id}")

        account = get_or_create(
            db.session, RhAccount, 'org_id',
            org_id=org_id
        )

        system_fields = self._build_system_fields(payload, account.id)

        # Add performance-specific fields
        system_fields.update({
            "cpu_states": payload.get('cpu_states'),
            "io_states": payload.get('io_states'),
            "memory_states": payload.get('memory_states'),
            "state": payload.get('state'),
            "instance_type": payload.get('instance_type'),
            "region": payload.get('region')
        })

        system = get_or_create(db.session, System, 'inventory_id', **system_fields)
        logging.info(
            f"{self.service} - System {inventory_id} ({system.id}) created/updated successfully."
        )

        performance_profile_fields = {
            "system_id": system.id,
            "performance_record": payload.get('performance_record'),
            "performance_utilization": payload.get('performance_utilization'),
            "report_date": datetime.now(timezone.utc),
            "rule_hit_details": payload.get('rule_hit_details'),
            "number_of_recommendations": payload.get('number_of_recommendations', 0),
            "state": payload.get('state'),
            "operating_system": payload.get('operating_system'),
            "psi_enabled": payload.get('psi_enabled'),
            "top_candidate": payload.get('top_candidate'),
            "top_candidate_price": payload.get('top_candidate_price')
        }

        insert_performance_profiles(db.session, system.id, performance_profile_fields)
        logging.info(
            f"{self.service} - Performance profile created/updated successfully for system: {inventory_id}"
        )

        db.session.commit()
        logging.info(
            f"{self.service} - Successfully processed system {system.inventory_id} ({system.id})"
        )


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    processor = ReportProcessorConsumer()
    processor.run()
