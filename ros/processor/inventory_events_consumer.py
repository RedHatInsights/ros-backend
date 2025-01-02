import json
import os
import sys
from prometheus_client import start_http_server
from ros.lib import consume
from ros.lib.app import app
from ros.extensions import db, cache
from ros.lib.utils import get_or_create, system_allowed_in_ros, update_system_record
from confluent_kafka import KafkaException
from ros.lib.models import RhAccount, System
from ros.lib.config import (
    INVENTORY_EVENTS_TOPIC,
    METRICS_PORT,
    get_logger,
    CACHE_TIMEOUT_FOR_DELETED_SYSTEM,
    CACHE_KEYWORD_FOR_DELETED_SYSTEM,
    GROUP_ID
)
from ros.lib.cw_logging import commence_cw_log_streaming, threadctx
from ros.processor.metrics import (processor_requests_success,
                                   processor_requests_failures,
                                   kafka_failures)

LOG = get_logger(__name__)


class InventoryEventsConsumer:
    """Inventory events consumer."""

    def __init__(self):
        """Create Inventory Events Consumer."""
        self.consumer = consume.init_consumer(INVENTORY_EVENTS_TOPIC, GROUP_ID)

        self.event_type_map = {
            'delete': self.host_delete_event,
            'created': self.host_create_update_events,
            'updated': self.host_create_update_events
        }
        self.prefix = 'INVENTORY EVENTS'
        self.reporter = 'INVENTORY EVENTS'

    def __iter__(self):
        return self

    def __next__(self):
        msg = self.consumer.poll()
        if msg is None:
            raise StopIteration
        return msg

    def run(self):
        """Initialize Consumer."""
        LOG.info(f"{self.prefix} - Processor is running. Awaiting msgs.")
        for msg in iter(self):
            if msg.error():
                LOG.error(f"{self.prefix} - Consumer error: {msg.error()}")
                kafka_failures.labels(reporter=self.reporter).inc()
                raise KafkaException(msg.error())

            account = None
            host_id = None
            org_id = None
            try:
                msg = json.loads(msg.value().decode("utf-8"))
                # SEE under consoledot documentation > services > inventory
                # where there is a section called event_interface to get
                # what keys present in event message.
                event_type = msg['type']
                metadata = msg['metadata']
                if event_type == 'delete':
                    account = msg['account']
                    host_id = msg['id']
                    org_id = msg['org_id']
                else:
                    account = msg['host']['account']
                    host_id = msg['host']['id']
                    org_id = msg['host'].get('org_id')

                threadctx.request_id = None
                if metadata is not None and isinstance(metadata, dict):
                    threadctx.request_id = metadata.get('request_id')
                threadctx.account = account
                threadctx.org_id = org_id

                if event_type in self.event_type_map.keys():
                    handler = self.event_type_map[event_type]
                    handler(msg)
                else:
                    LOG.info(
                        f"{self.prefix} - Unknown event of type {event_type}"
                    )
            except json.decoder.JSONDecodeError:
                kafka_failures.labels(reporter=self.reporter).inc()
                LOG.error(
                    f"{self.prefix} - Unable to decode kafka message: {msg.value()}"
                )
            except Exception as err:
                processor_requests_failures.labels(
                    reporter=self.reporter, org_id=org_id
                ).inc()
                _exc_type, _exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                LOG.error(
                    f"{self.prefix} - An error occurred: {repr(err)}"
                    f" in {fname} at {exc_tb.tb_lineno} for a system {host_id}"
                    f" from account: {account} & org_id: {org_id}"
                )
            finally:
                self.consumer.commit()
        LOG.warning("Stopping inventory consumer")
        self.consumer.close()

    def host_delete_event(self, msg):
        """Process delete message."""
        self.prefix = "INVENTORY DELETE EVENT"
        host_id = msg['id']
        with app.app_context():
            LOG.debug(
                f"{self.prefix} - Received a message for system with inventory_id {host_id}"
            )

            rows_deleted = db.session.execute(db.delete(System).filter(System.inventory_id == host_id))
            db.session.commit()

            if rows_deleted.rowcount == 1:
                processor_requests_success.labels(
                    reporter=self.reporter, org_id=msg['org_id']
                ).inc()
                LOG.info(
                    f"{self.prefix} - Deleted system with inventory id: {host_id}"
                )
                cache_key = (f"{msg['org_id']}{CACHE_KEYWORD_FOR_DELETED_SYSTEM}"
                             f'{host_id}')
                cache.set(
                    cache_key, 1, timeout=CACHE_TIMEOUT_FOR_DELETED_SYSTEM
                )

    def host_create_update_events(self, msg):
        """ Process created/updated message ( create system record, store new report )"""
        self.prefix = "INVENTORY Update EVENT" if msg['type'] == 'updated' else "INVENTORY CREATE EVENT"
        if system_allowed_in_ros(msg, self.reporter):
            LOG.info(
                f"{self.prefix} - Processing a message for system({msg['host']['id']}) "
                f"belonging to account: {msg['host']['account']} and org_id: {msg['host'].get('org_id')}"
            )
            self.process_system_details(msg)

    def process_system_details(self, msg):
        """ Store new system information (stale, stale_warning timestamp) and return internal DB id"""
        host = msg['host']
        with app.app_context():
            if (msg.get('type') == 'updated'):
                system_fields = {
                    "inventory_id": host['id'],
                    "display_name": host['display_name'],
                    "fqdn": host['fqdn'],
                    "stale_timestamp": host['stale_timestamp'],
                    "groups": host.get('groups', [])
                }

                operating_system = host['system_profile'].get('operating_system')
                cloud_provider = host['system_profile'].get('cloud_provider')
                if (operating_system is not None):
                    system_fields.update({"operating_system": operating_system})
                if (cloud_provider is not None):
                    system_fields.update({"cloud_provider": cloud_provider})

                system = update_system_record(db.session, **system_fields)
                if system is not None:
                    db.session.commit()
                    account = db.session.scalar(db.select(RhAccount).filter_by(id=system.tenant_id))
                    processor_requests_success.labels(
                        reporter=self.reporter, org_id=account.org_id
                    ).inc()
                    LOG.info(
                        f"{self.prefix} - Refreshed system {system.inventory_id} ({system.id}) "
                        f"belonging to account: {account.account} ({account.id}) and org_id: {account.org_id}"
                    )
                    self.expired_del_cache_if_exists(
                        host['id'], account.org_id
                    )
            else:
                try:
                    account = get_or_create(
                        db.session, RhAccount, 'org_id',
                        account=host['account'],
                        org_id=host.get('org_id')
                    )

                    system_fields = {
                        "tenant_id": account.id,
                        "inventory_id": host['id'],
                        "display_name": host['display_name'],
                        "fqdn": host['fqdn'],
                        "cloud_provider": host['system_profile']['cloud_provider'],
                        "stale_timestamp": host['stale_timestamp'],
                        "operating_system": host['system_profile'].get('operating_system'),
                        "groups": host.get('groups', [])
                    }
                    system = get_or_create(db.session, System, 'inventory_id', **system_fields)

                    # Commit changes
                    db.session.commit()
                    processor_requests_success.labels(
                        reporter=self.reporter, org_id=account.org_id
                    ).inc()
                    LOG.info(
                        f"{self.prefix} - Refreshed system {system.inventory_id} ({system.id}) "
                        f"belonging to account: {account.account} ({account.id}) and org_id: {account.org_id}"
                    )
                    self.expired_del_cache_if_exists(
                        host['id'], account.org_id
                    )
                except Exception as err:
                    processor_requests_failures.labels(
                        reporter=self.reporter, org_id=account.org_id
                    ).inc()

                    LOG.error(
                        f"{self.prefix} - Unable to add system {host['id']} to DB "
                        f"belonging to account: {account.account} and org_id: {account.org_id} - {err}"
                    )

    def expired_del_cache_if_exists(self, host_id, org_id):
        with app.app_context():
            cache_key = (f"{org_id}{CACHE_KEYWORD_FOR_DELETED_SYSTEM}"
                         f'{host_id}')
            if cache.get(cache_key):
                cache.delete(cache_key)


if __name__ == "__main__":
    start_http_server(int(METRICS_PORT))
    cache.init_app(app)
    commence_cw_log_streaming('ros-processor')
    processor = InventoryEventsConsumer()
    processor.run()
