from ros.lib.models import System
from ros.extensions import db


def db_get_host(host_id):
    return db.session.scalar(db.select(System).filter_by(inventory_id=host_id))


def db_get_record(model, **filters):
    return db.session.scalar(db.select(model).filter_by(**filters))


def db_get_records(model, **filters):
    return db.session.query(model).filter_by(**filters)
